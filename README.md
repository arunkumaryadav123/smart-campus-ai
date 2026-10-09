# Smart Campus AI 🎓

A full-stack student project that brings campus announcements, student requests, role-based login, and a local FAQ assistant into one portal.

## Features
- **Role-based login:** Admin, Faculty, and Student demo accounts.
- **Announcements:** Admin and Faculty can publish updates; signed-in users can read them.
- **Campus requests:** Users can submit and track requests. Admin can view all requests.
- **Campus AI assistant:** Answers common questions about library hours, Wi-Fi, fees, attendance, and maintenance without an API key.
- **SQLite persistence:** Accounts, sessions, announcements, and requests persist locally.
- **Responsive UI** for desktop and mobile.
- **Health endpoint:** `GET /api/health`.

## Tech stack
- Frontend: HTML, CSS, JavaScript
- Backend: Python + FastAPI
- Database: SQLite
- Assistant: local rule-based FAQ engine

## Requirements
Python 3.10 or newer.

## Run on Windows (PowerShell)
```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload
```

## Run the automated tests

Install the development dependencies and run the regression suite:

```bash
pip install -r requirements-dev.txt
pytest -q
```

GitHub Actions also runs Python compilation and API regression tests on pushes and pull requests to `main`.

## Run on macOS / Linux
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Open http://127.0.0.1:8000 in your browser. The SQLite database and demo accounts are created automatically on first startup. Interactive API docs are available at http://127.0.0.1:8000/docs.

## Demo credentials

| Role | Username | Password |
|---|---|---|
| Admin | `admin` | `admin123` |
| Faculty | `faculty` | `faculty123` |
| Student | `student` | `student123` |

These are for local demonstration only. Do not deploy a public instance with demo credentials.

## API endpoints

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/api/health` | Check server status |
| POST | `/api/login` | Sign in |
| GET | `/api/me` | Current user |
| GET / POST | `/api/announcements` | Read or publish announcements |
| GET / POST | `/api/tasks` | Read or create campus requests |
| PATCH | `/api/tasks/{task_id}/close` | Close a request |
| POST | `/api/assistant` | Ask Campus AI |

## Project structure
```text
smart-campus-ai/
├── app/
│   ├── main.py
│   └── static/
│       ├── index.html
│       ├── styles.css
│       └── app.js
├── .gitignore
├── requirements.txt
└── README.md
```

## Important limitations
This is an educational prototype, not a production university system. The FAQ assistant does not use a language model and cannot access live timetable, attendance, fee, or Wi-Fi systems. The simple password hashing is not suitable for production. Before public deployment, use Argon2/bcrypt, add rate limiting and appropriate CSRF/security protections, use HTTPS, configure secrets, and review authorization and privacy requirements. Do not use real student records in this demo.

## Suggested extensions
- Connect a verified campus timetable or student information API.
- Add request categories, priority, and admin assignment.
- Add email or in-app notifications.
- Connect a real LLM with a server-side API key and campus-approved knowledge base.
- Add automated tests and deployment configuration.
