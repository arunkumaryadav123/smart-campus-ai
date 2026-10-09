# Smart Campus AI 🎓

A full-stack campus portal built with FastAPI, SQLite, HTML, CSS, and JavaScript. It includes role-based login, campus announcements, campus requests, admin user management, and a local FAQ assistant.

## Features

- SQLite database for users, sessions, announcements, and requests; database path is configurable with `DATABASE_PATH`.
- Three roles: admin, faculty, and student, with API-side permission checks.
- Admin user management, announcements, campus requests, and local FAQ assistant.
- Server-side session invalidation on logout.
- GitHub Actions runs Python compilation, JavaScript syntax checks, and API tests.

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

Open http://127.0.0.1:8000. API documentation: http://127.0.0.1:8000/docs. The database and starter announcements are initialized automatically.

## Local demo accounts

| Role | Username | Password |
|---|---|---|
| Admin | `admin` | `admin123` |
| Faculty | `faculty` | `faculty123` |
| Student | `student` | `student123` |

These are demo credentials for local development only. The deployed Blueprint generates a separate admin password; do not use demo credentials for real student data.

## Test the project

```bash
pip install -r requirements-dev.txt
pytest -q
```

## Free Render preview deployment

The repository includes `render.yaml` configured for a **free Render web service**.

1. Open [Render Blueprint deployment](https://render.com/deploy?repo=https://github.com/arunkumaryadav123/smart-campus-ai).
2. Connect to GitHub if prompted and select `arunkumaryadav123/smart-campus-ai`.
3. Review the detected Blueprint, then apply/create the service using the free instance option.
4. Wait for the deploy to finish and open the `onrender.com` URL shown by Render.
5. Find the generated `ADMIN_PASSWORD` in the Render service's Environment settings. The admin username is `admin`.

The free preview uses an **ephemeral filesystem** and stores SQLite at `/tmp/campus.db`. This is suitable for a student demo, but database contents can disappear when the service restarts, redeploys, or its instance is replaced. The free web service may also spin down when idle and take a little time to wake up. For durable production data, use a persistent storage/database plan.

Health check: `/api/health`. API docs: `/docs`.

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

## Important limitations and security

This is a student-project prototype, not a production university information system. The assistant is a local FAQ engine, not connected to a real university timetable, attendance, fee system, or Wi-Fi directory. Do not store real student records until privacy, access control, backups, and security have been reviewed. Keep the generated admin password private.
