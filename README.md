# Smart Campus AI

A demo smart campus web app with role-based login for admin, faculty, and students; campus announcements and requests; SQLite persistence; and a local FAQ assistant.

## Run locally

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Open http://127.0.0.1:8000

See the project ZIP for the complete application files and setup instructions.