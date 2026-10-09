# Smart Campus AI 🎓

A full-stack campus portal built with FastAPI, SQLite, HTML, CSS, and JavaScript. It includes role-based login, persistent campus announcements, campus requests, admin user management, and a local FAQ assistant.

## Features

- **Persistent database:** SQLite tables for users, sessions, announcements, and requests. The database path is configurable with `DATABASE_PATH`.
- **Three roles:** Admin, faculty, and student, with API-side permission checks.
- **User management:** Admins can create and list accounts from the website.
- **Announcements:** Admin and faculty can publish updates; signed-in users can read them.
- **Campus requests:** Users can submit and track requests; admins can see all requests and close them.
- **Campus assistant:** Local FAQ answers about library hours, timetable guidance, Wi-Fi, fees, attendance, and maintenance.
- **Session logout:** Signing out invalidates the server-side session token.
- **Automated checks:** GitHub Actions runs Python compilation and API tests.

## Run locally

Python 3.10 or newer is recommended.

### Windows (PowerShell)

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload
```

### macOS / Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Open http://127.0.0.1:8000. API documentation: http://127.0.0.1:8000/docs. Database tables and starter data are initialized automatically on first startup.

## Local demo accounts

| Role | Username | Password |
|---|---|---|
| Admin | `admin` | `admin123` |
| Faculty | `faculty` | `faculty123` |
| Student | `student` | `student123` |

The demo accounts are seeded by default for local development. After signing in as admin, use **Manage users** to create additional accounts. Passwords created by the app are stored as PBKDF2 hashes; legacy demo hashes are upgraded when the user signs in successfully.

## Test the project

```bash
pip install -r requirements-dev.txt
pytest -q
```

The tests cover health/database connectivity, all demo logins, authorization, announcements, requests, assistant responses, user management, logout, and database persistence across connections.

## Deploy with a persistent database on Render

The repository includes `render.yaml` for a Render Blueprint deployment. It configures a persistent disk at `/var/data` and uses `/var/data/campus.db` as the SQLite database path. **A persistent disk requires a paid Render web-service plan**; do not remove the disk if you need data to survive restarts/redeploys.

1. Push this repository to GitHub (already done).
2. Open [Render Blueprint deployment](https://render.com/deploy?repo=https://github.com/arunkumaryadav123/smart-campus-ai).
3. Review the service and disk settings, then create the deployment.
4. Wait for the deploy and open the generated `onrender.com` URL.
5. In the Render dashboard, open the service's environment settings and keep the generated `ADMIN_PASSWORD` secret safe. The deployment disables the faculty/student demo accounts by default.
6. Sign in with username `admin` and the generated admin password. Use **Manage users** to create faculty and student accounts.

Render runs the same FastAPI application and checks `/api/health` before marking the service healthy. If you deploy somewhere else, configure `DATABASE_PATH` to a persistent writable disk path; ephemeral filesystems can lose SQLite data when an instance restarts or is replaced.

## API endpoints

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/api/health` | App and database health |
| POST | `/api/login` | Sign in |
| POST | `/api/logout` | Invalidate session |
| GET | `/api/me` | Current user |
| GET / POST | `/api/users` | Admin list/create users |
| GET / POST | `/api/announcements` | Read/publish announcements |
| GET / POST | `/api/tasks` | Read/create campus requests |
| PATCH | `/api/tasks/{task_id}/close` | Close a request |
| POST | `/api/assistant` | Ask the local FAQ assistant |

## Project structure

```text
smart-campus-ai/
├── app/
│   ├── main.py
│   └── static/
│       ├── index.html
│       ├── styles.css
│       └── app.js
├── tests/test_app.py
├── .github/workflows/tests.yml
├── requirements.txt
├── requirements-dev.txt
├── render.yaml
└── README.md
```

## Important limitations and security

This is a student-project prototype, not a production university information system. The assistant is a local FAQ engine; it is not connected to a real university timetable, attendance, fee system, or Wi-Fi directory. Use HTTPS, keep admin credentials private, back up the persistent database, and do not store real student records until privacy, access control, backup, and security requirements have been reviewed. The Render Blueprint seeds only the admin account; local demo accounts are disabled in that deployment configuration.
