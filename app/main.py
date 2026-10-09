from contextlib import asynccontextmanager, contextmanager
from datetime import datetime, timezone
from pathlib import Path
import hashlib
import hmac
import os
import secrets
import sqlite3

from fastapi import FastAPI, Header, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, field_validator

ROOT = Path(__file__).resolve().parent
DB_PATH = Path(os.getenv("DATABASE_PATH", str(ROOT / "campus.db"))).expanduser()
ROLES = {"admin", "faculty", "student"}


@contextmanager
def db():
    """Open one SQLite connection per operation and always close it."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(DB_PATH, timeout=15)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    con.execute("PRAGMA busy_timeout = 15000")
    try:
        yield con
        con.commit()
    except Exception:
        con.rollback()
        raise
    finally:
        con.close()


def now_iso():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 310_000)
    return "pbkdf2_sha256$310000$" + salt.hex() + "$" + digest.hex()


def verify_password(password: str, stored: str) -> bool:
    # Upgrade legacy SHA-256 demo hashes on successful login.
    if not stored.startswith("pbkdf2_sha256$"):
        return hmac.compare_digest(hashlib.sha256(password.encode("utf-8")).hexdigest(), stored)
    try:
        _, iterations, salt_hex, digest_hex = stored.split("$", 3)
        actual = hashlib.pbkdf2_hmac(
            "sha256", password.encode("utf-8"), bytes.fromhex(salt_hex), int(iterations)
        ).hex()
        return hmac.compare_digest(actual, digest_hex)
    except (ValueError, TypeError):
        return False


def add_user(con, username, password, name, role):
    con.execute(
        "INSERT OR IGNORE INTO users(username,password_hash,name,role) VALUES(?,?,?,?)",
        (username.strip().lower(), hash_password(password), name.strip(), role),
    )


def init_db():
    with db() as con:
        con.execute("PRAGMA journal_mode = WAL")
        con.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            name TEXT NOT NULL,
            role TEXT NOT NULL CHECK(role IN ('admin','faculty','student'))
        );
        CREATE TABLE IF NOT EXISTS sessions (
            token TEXT PRIMARY KEY,
            user_id INTEGER NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
        );
        CREATE TABLE IF NOT EXISTS announcements (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            body TEXT NOT NULL,
            author TEXT NOT NULL,
            created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT NOT NULL,
            owner TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'Open' CHECK(status IN ('Open','Closed')),
            created_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_sessions_user_id ON sessions(user_id);
        CREATE INDEX IF NOT EXISTS idx_tasks_owner ON tasks(owner);
        CREATE INDEX IF NOT EXISTS idx_announcements_created ON announcements(id DESC);
        """)

        admin_username = os.getenv("ADMIN_USERNAME", "admin").strip().lower()
        admin_password = os.getenv("ADMIN_PASSWORD", "admin123")
        admin_name = os.getenv("ADMIN_NAME", "Campus Administrator")
        if admin_username and admin_password:
            add_user(con, admin_username, admin_password, admin_name, "admin")

        if os.getenv("SEED_DEMO_USERS", "true").strip().lower() in {"1", "true", "yes"}:
            add_user(con, "faculty", "faculty123", "Demo Faculty", "faculty")
            add_user(con, "student", "student123", "Demo Student", "student")

        count = con.execute("SELECT COUNT(*) AS n FROM announcements").fetchone()["n"]
        if count == 0:
            con.execute(
                "INSERT INTO announcements(title,body,author,created_at) VALUES(?,?,?,?)",
                ("Welcome to Smart Campus AI",
                 "Use this portal to view campus updates, create requests, and ask the campus assistant.",
                 "Admin", now_iso()),
            )
            con.execute(
                "INSERT INTO announcements(title,body,author,created_at) VALUES(?,?,?,?)",
                ("Library hours",
                 "The demo library schedule is Monday–Saturday, 9:00 AM–6:00 PM. Confirm actual timings with campus staff.",
                 "Admin", now_iso()),
            )


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title="Smart Campus AI", version="1.1.0", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=ROOT / "static"), name="static")


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=80)
    password: str = Field(min_length=1, max_length=256)


class UserCreateRequest(BaseModel):
    username: str = Field(min_length=3, max_length=40, pattern=r"^[a-zA-Z0-9_.-]+$")
    password: str = Field(min_length=8, max_length=256)
    name: str = Field(min_length=2, max_length=100)
    role: str

    @field_validator("role")
    @classmethod
    def valid_role(cls, value):
        if value not in ROLES:
            raise ValueError("Role must be admin, faculty, or student.")
        return value


class AnnouncementRequest(BaseModel):
    title: str = Field(min_length=3, max_length=120)
    body: str = Field(min_length=3, max_length=2000)


class TaskRequest(BaseModel):
    title: str = Field(min_length=3, max_length=120)
    description: str = Field(min_length=3, max_length=2000)


class AskRequest(BaseModel):
    question: str = Field(min_length=2, max_length=1000)


def current_user(authorization: str | None):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Please sign in again.")
    token = authorization[7:].strip()
    if not token:
        raise HTTPException(status_code=401, detail="Please sign in again.")
    with db() as con:
        row = con.execute(
            """SELECT users.id, users.username, users.name, users.role
               FROM sessions JOIN users ON users.id=sessions.user_id
               WHERE sessions.token=?""",
            (token,),
        ).fetchone()
    if not row:
        raise HTTPException(status_code=401, detail="Session expired. Please sign in again.")
    return dict(row)


def require_role(user, *roles):
    if user["role"] not in roles:
        raise HTTPException(status_code=403, detail="Your account role cannot perform this action.")


@app.get("/", response_class=HTMLResponse)
def home():
    return (ROOT / "static" / "index.html").read_text(encoding="utf-8")


@app.get("/api/health")
def health():
    with db() as con:
        con.execute("SELECT 1").fetchone()
    return {"status": "ok", "database": "connected", "app": "Smart Campus AI"}


@app.post("/api/login")
def login(payload: LoginRequest):
    with db() as con:
        user = con.execute("SELECT * FROM users WHERE username=?", (payload.username.strip().lower(),)).fetchone()
        if not user or not verify_password(payload.password, user["password_hash"]):
            raise HTTPException(status_code=401, detail="Incorrect username or password.")
        if not user["password_hash"].startswith("pbkdf2_sha256$"):
            con.execute("UPDATE users SET password_hash=? WHERE id=?", (hash_password(payload.password), user["id"]))
        token = secrets.token_urlsafe(32)
        con.execute("INSERT INTO sessions(token,user_id,created_at) VALUES(?,?,?)", (token, user["id"], now_iso()))
    return {"token": token, "user": {"username": user["username"], "name": user["name"], "role": user["role"]}}


@app.post("/api/logout")
def logout(authorization: str | None = Header(default=None)):
    if authorization and authorization.startswith("Bearer "):
        with db() as con:
            con.execute("DELETE FROM sessions WHERE token=?", (authorization[7:].strip(),))
    return {"ok": True}


@app.get("/api/me")
def me(authorization: str | None = Header(default=None)):
    return current_user(authorization)


@app.get("/api/users")
def users(authorization: str | None = Header(default=None)):
    user = current_user(authorization)
    require_role(user, "admin")
    with db() as con:
        rows = con.execute("SELECT id,username,name,role FROM users ORDER BY role,username").fetchall()
    return [dict(row) for row in rows]


@app.post("/api/users", status_code=201)
def create_user(payload: UserCreateRequest, authorization: str | None = Header(default=None)):
    actor = current_user(authorization)
    require_role(actor, "admin")
    username = payload.username.strip().lower()
    with db() as con:
        exists = con.execute("SELECT 1 FROM users WHERE username=?", (username,)).fetchone()
        if exists:
            raise HTTPException(status_code=409, detail="That username already exists.")
        con.execute(
            "INSERT INTO users(username,password_hash,name,role) VALUES(?,?,?,?)",
            (username, hash_password(payload.password), payload.name.strip(), payload.role),
        )
        row = con.execute("SELECT id,username,name,role FROM users WHERE username=?", (username,)).fetchone()
    return dict(row)


@app.get("/api/announcements")
def announcements(authorization: str | None = Header(default=None)):
    current_user(authorization)
    with db() as con:
        rows = con.execute("SELECT * FROM announcements ORDER BY id DESC").fetchall()
    return [dict(row) for row in rows]


@app.post("/api/announcements", status_code=201)
def create_announcement(payload: AnnouncementRequest, authorization: str | None = Header(default=None)):
    user = current_user(authorization)
    require_role(user, "admin", "faculty")
    with db() as con:
        con.execute(
            "INSERT INTO announcements(title,body,author,created_at) VALUES(?,?,?,?)",
            (payload.title.strip(), payload.body.strip(), user["name"], now_iso()),
        )
    return {"ok": True}


@app.get("/api/tasks")
def tasks(authorization: str | None = Header(default=None)):
    user = current_user(authorization)
    with db() as con:
        if user["role"] == "admin":
            rows = con.execute("SELECT * FROM tasks ORDER BY id DESC").fetchall()
        else:
            rows = con.execute("SELECT * FROM tasks WHERE owner=? ORDER BY id DESC", (user["username"],)).fetchall()
    return [dict(row) for row in rows]


@app.post("/api/tasks", status_code=201)
def create_task(payload: TaskRequest, authorization: str | None = Header(default=None)):
    user = current_user(authorization)
    with db() as con:
        con.execute(
            "INSERT INTO tasks(title,description,owner,status,created_at) VALUES(?,?,?,?,?)",
            (payload.title.strip(), payload.description.strip(), user["username"], "Open", now_iso()),
        )
    return {"ok": True}


@app.patch("/api/tasks/{task_id}/close")
def close_task(task_id: int, authorization: str | None = Header(default=None)):
    user = current_user(authorization)
    with db() as con:
        task = con.execute("SELECT * FROM tasks WHERE id=?", (task_id,)).fetchone()
        if not task:
            raise HTTPException(status_code=404, detail="Request not found.")
        if user["role"] != "admin" and task["owner"] != user["username"]:
            raise HTTPException(status_code=403, detail="You can only update your own requests.")
        con.execute("UPDATE tasks SET status='Closed' WHERE id=?", (task_id,))
    return {"ok": True}


@app.post("/api/assistant")
def assistant(payload: AskRequest, authorization: str | None = Header(default=None)):
    user = current_user(authorization)
    q = payload.question.lower()
    if any(w in q for w in ["library", "book"]):
        answer = "The demo library schedule is Monday–Saturday, 9:00 AM–6:00 PM. Please confirm real opening hours with campus staff."
    elif any(w in q for w in ["timetable", "schedule", "class", "lecture"]):
        answer = "I don't have your live timetable connected yet. Check your department notice board or ask faculty to publish an announcement here."
    elif any(w in q for w in ["fee", "payment", "tuition"]):
        answer = "For fee balances or payment issues, contact the campus accounts office. Do not share card PINs or passwords in this portal."
    elif any(w in q for w in ["wifi", "internet", "network"]):
        answer = "For campus Wi-Fi, check the official network name and credentials with IT support. Never share your password in a public request."
    elif any(w in q for w in ["attendance", "present"]):
        answer = "Attendance records are not connected in this demo. Contact your faculty or department office for the official record."
    elif any(w in q for w in ["complaint", "issue", "request", "broken", "maintenance"]):
        answer = "You can create a campus request in the Requests section. Include the location and a clear description; avoid posting private information."
    elif any(w in q for w in ["hello", "hi", "hey"]):
        answer = f"Hi {user['name']}! I can help with library, timetable, Wi-Fi, fees, attendance, and campus requests."
    else:
        answer = "I can help with library hours, timetable guidance, Wi-Fi, fees, attendance, and campus requests. For official or live data, contact the relevant campus office."
    return {"answer": answer, "mode": "local-faq", "note": "Demo assistant; not connected to live university systems."}
