"""Student analytics endpoints for the Smart Campus AI demo."""
import json
from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, Field

from .main import db, current_user, require_role, now_iso

router = APIRouter(prefix="/api/analytics", tags=["student analytics"])

# Seed data is clearly marked as fictional demo data.
SEED_STUDENTS = [
    ("student", "Demo Student", "CSE-A", 82, 18, 20, [78, 84, 81]),
    ("ananya", "Ananya Sharma", "CSE-A", 96, 24, 25, [91, 88, 94]),
    ("rahul", "Rahul Verma", "CSE-A", 68, 17, 25, [62, 71, 65]),
    ("priya", "Priya Patel", "CSE-B", 91, 23, 25, [87, 92, 90]),
    ("arjun", "Arjun Reddy", "CSE-B", 74, 18, 25, [69, 73, 76]),
    ("sneha", "Sneha Iyer", "CSE-A", 88, 22, 25, [85, 89, 91]),
]

def ensure_schema():
    with db() as con:
        con.execute("""CREATE TABLE IF NOT EXISTS student_metrics (
            username TEXT PRIMARY KEY,
            full_name TEXT NOT NULL,
            section TEXT NOT NULL DEFAULT 'CSE-A',
            attendance_present INTEGER NOT NULL DEFAULT 0,
            attendance_total INTEGER NOT NULL DEFAULT 0,
            assignments_done INTEGER NOT NULL DEFAULT 0,
            assignments_total INTEGER NOT NULL DEFAULT 0,
            marks_json TEXT NOT NULL DEFAULT '[]',
            updated_at TEXT NOT NULL
        )""")
        for username, name, section, attendance_pct, done, total, marks in SEED_STUDENTS:
            present = round(attendance_pct * 25 / 100)
            con.execute("""INSERT OR IGNORE INTO student_metrics
                (username,full_name,section,attendance_present,attendance_total,
                 assignments_done,assignments_total,marks_json,updated_at)
                 VALUES(?,?,?,?,?,?,?,?,?)""",
                (username, name, section, present, 25, done, total, json.dumps(marks), now_iso()))

def serialize(row):
    d = dict(row)
    d["attendance_rate"] = round(100 * d["attendance_present"] / d["attendance_total"]) if d["attendance_total"] else 0
    d["assignment_rate"] = round(100 * d["assignments_done"] / d["assignments_total"]) if d["assignments_total"] else 0
    d["marks"] = json.loads(d.pop("marks_json"))
    d["average_marks"] = round(sum(d["marks"]) / len(d["marks"])) if d["marks"] else 0
    d["risk"] = "High" if d["attendance_rate"] < 75 or d["average_marks"] < 65 else ("Medium" if d["attendance_rate"] < 85 or d["average_marks"] < 75 else "Low")
    return d

class MetricUpdate(BaseModel):
    full_name: str = Field(min_length=2, max_length=100)
    section: str = Field(min_length=1, max_length=20)
    attendance_present: int = Field(ge=0, le=500)
    attendance_total: int = Field(ge=1, le=500)
    assignments_done: int = Field(ge=0, le=500)
    assignments_total: int = Field(ge=1, le=500)
    marks: list[int] = Field(min_length=1, max_length=20)

@router.get("/overview")
def overview(authorization: str | None = Header(default=None)):
    user = current_user(authorization)
    ensure_schema()
    with db() as con:
        if user["role"] == "student":
            rows = con.execute("SELECT * FROM student_metrics WHERE username=?", (user["username"],)).fetchall()
        else:
            rows = con.execute("SELECT * FROM student_metrics ORDER BY full_name").fetchall()
    data = [serialize(r) for r in rows]
    if user["role"] == "student" and not data:
        raise HTTPException(status_code=404, detail="No analytics record is available for your account yet.")
    if user["role"] == "student":
        s = data[0]
        return {"role": user["role"], "student_count": 1, "average_attendance": s["attendance_rate"],
                "average_marks": s["average_marks"], "assignment_completion": s["assignment_rate"],
                "high_risk_count": int(s["risk"] == "High"), "students": data}
    return {"role": user["role"], "student_count": len(data),
            "average_attendance": round(sum(s["attendance_rate"] for s in data)/len(data)) if data else 0,
            "average_marks": round(sum(s["average_marks"] for s in data)/len(data)) if data else 0,
            "assignment_completion": round(sum(s["assignment_rate"] for s in data)/len(data)) if data else 0,
            "high_risk_count": sum(s["risk"] == "High" for s in data), "students": data}

@router.get("/students/{username}")
def get_student(username: str, authorization: str | None = Header(default=None)):
    user = current_user(authorization)
    ensure_schema()
    if user["role"] == "student" and user["username"] != username:
        raise HTTPException(status_code=403, detail="Students can only view their own analytics.")
    with db() as con:
        row = con.execute("SELECT * FROM student_metrics WHERE username=?", (username.lower(),)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Student analytics record not found.")
    return serialize(row)

@router.put("/students/{username}")
def update_student(username: str, payload: MetricUpdate, authorization: str | None = Header(default=None)):
    user = current_user(authorization)
    require_role(user, "admin", "faculty")
    ensure_schema()
    if payload.attendance_present > payload.attendance_total:
        raise HTTPException(status_code=422, detail="Present classes cannot exceed total classes.")
    if payload.assignments_done > payload.assignments_total:
        raise HTTPException(status_code=422, detail="Completed assignments cannot exceed total assignments.")
    if any(mark < 0 or mark > 100 for mark in payload.marks):
        raise HTTPException(status_code=422, detail="Marks must be between 0 and 100.")
    with db() as con:
        exists = con.execute("SELECT 1 FROM student_metrics WHERE username=?", (username.lower(),)).fetchone()
        if not exists:
            raise HTTPException(status_code=404, detail="Student analytics record not found.")
        con.execute("""UPDATE student_metrics SET full_name=?,section=?,attendance_present=?,
            attendance_total=?,assignments_done=?,assignments_total=?,marks_json=?,updated_at=?
            WHERE username=?""",
            (payload.full_name.strip(), payload.section.strip(), payload.attendance_present,
             payload.attendance_total, payload.assignments_done, payload.assignments_total,
             json.dumps(payload.marks), now_iso(), username.lower()))
        row = con.execute("SELECT * FROM student_metrics WHERE username=?", (username.lower(),)).fetchone()
    return serialize(row)

@router.get("/study-plan")
def study_plan(authorization: str | None = Header(default=None)):
    user = current_user(authorization)
    ensure_schema()
    with db() as con:
        row = con.execute("SELECT * FROM student_metrics WHERE username=?", (user["username"],)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="No analytics record is available for your account yet.")
    s = serialize(row)
    tasks = []
    if s["attendance_rate"] < 75:
        tasks.append({"priority":"High","title":"Improve attendance","detail":f"Your attendance is {s['attendance_rate']}%. Attend upcoming classes and contact faculty about missed lessons."})
    if s["average_marks"] < 70:
        tasks.append({"priority":"High","title":"Revise weak topics","detail":"Review your last assessment, list three difficult concepts, and practise five questions for each."})
    if s["assignment_rate"] < 80:
        tasks.append({"priority":"Medium","title":"Finish pending assignments","detail":f"You have completed {s['assignments_done']} of {s['assignments_total']} assignments. Schedule a focused catch-up session."})
    if not tasks:
        tasks.append({"priority":"Low","title":"Maintain your progress","detail":"Keep attendance steady, review notes for 20 minutes daily, and prepare for the next assessment early."})
    tasks.append({"priority":"Medium","title":"Use a focused study block","detail":"Try 25 minutes of distraction-free study followed by a 5-minute break."})
    return {"student":s["full_name"],"generated_at":now_iso(),"tasks":tasks,
            "disclaimer":"Recommendations use fictional demo metrics. They are guidance, not official academic decisions."}
