import pytest
from fastapi.testclient import TestClient

import app.main as campus


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(campus, "DB_PATH", tmp_path / "campus-test.db")
    with TestClient(campus.app) as test_client:
        yield test_client


def login(client, username, password):
    response = client.post("/api/login", json={"username": username, "password": password})
    assert response.status_code == 200, response.text
    return response.json()["token"]


def headers(token):
    return {"Authorization": f"Bearer {token}"}


def test_health_endpoint(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


@pytest.mark.parametrize(
    ("username", "password", "role"),
    [
        ("admin", "admin123", "admin"),
        ("faculty", "faculty123", "faculty"),
        ("student", "student123", "student"),
    ],
)
def test_demo_accounts_can_sign_in(client, username, password, role):
    token = login(client, username, password)
    response = client.get("/api/me", headers=headers(token))
    assert response.status_code == 200
    assert response.json()["role"] == role


def test_invalid_login_is_rejected(client):
    response = client.post("/api/login", json={"username": "student", "password": "wrong"})
    assert response.status_code == 401


def test_private_endpoints_require_login(client):
    assert client.get("/api/announcements").status_code == 401
    assert client.get("/api/tasks").status_code == 401


def test_student_cannot_publish_announcement(client):
    token = login(client, "student", "student123")
    response = client.post(
        "/api/announcements",
        headers=headers(token),
        json={"title": "Student announcement", "body": "This should be blocked."},
    )
    assert response.status_code == 403


def test_faculty_can_publish_announcement(client):
    token = login(client, "faculty", "faculty123")
    response = client.post(
        "/api/announcements",
        headers=headers(token),
        json={"title": "Exam notice", "body": "The lab exam starts at 10 AM."},
    )
    assert response.status_code == 201
    items = client.get("/api/announcements", headers=headers(token)).json()
    assert any(item["title"] == "Exam notice" for item in items)


def test_student_can_create_and_view_request(client):
    token = login(client, "student", "student123")
    created = client.post(
        "/api/tasks",
        headers=headers(token),
        json={"title": "Wi-Fi issue", "description": "Wi-Fi is not working in Block B."},
    )
    assert created.status_code == 201
    items = client.get("/api/tasks", headers=headers(token)).json()
    assert len(items) == 1
    assert items[0]["title"] == "Wi-Fi issue"
    assert items[0]["status"] == "Open"


def test_admin_can_view_and_close_request(client):
    student_token = login(client, "student", "student123")
    client.post(
        "/api/tasks",
        headers=headers(student_token),
        json={"title": "Broken light", "description": "Light is broken in room 12."},
    )
    admin_token = login(client, "admin", "admin123")
    tasks = client.get("/api/tasks", headers=headers(admin_token)).json()
    assert len(tasks) == 1
    response = client.patch(f"/api/tasks/{tasks[0]['id']}/close", headers=headers(admin_token))
    assert response.status_code == 200
    assert client.get("/api/tasks", headers=headers(admin_token)).json()[0]["status"] == "Closed"


def test_assistant_returns_local_faq_answer(client):
    token = login(client, "student", "student123")
    response = client.post(
        "/api/assistant",
        headers=headers(token),
        json={"question": "What are the library hours?"},
    )
    assert response.status_code == 200
    assert "library" in response.json()["answer"].lower()
    assert response.json()["mode"] == "local-faq"


def test_static_frontend_is_served(client):
    response = client.get("/")
    assert response.status_code == 200
    assert "Smart Campus AI" in response.text
    assert client.get("/static/app.js").status_code == 200



def test_database_data_survives_reopening_connection(client):
    token = login(client, "student", "student123")
    response = client.post(
        "/api/tasks",
        headers=headers(token),
        json={"title": "Persistent request", "description": "Confirm database data is retained."},
    )
    assert response.status_code == 201
    # The next request opens a fresh SQLite connection to the same database file.
    items = client.get("/api/tasks", headers=headers(token)).json()
    assert any(item["title"] == "Persistent request" for item in items)


def test_admin_can_create_and_list_users(client):
    admin_token = login(client, "admin", "admin123")
    response = client.post(
        "/api/users",
        headers=headers(admin_token),
        json={"username": "new.faculty", "password": "strongpass123", "name": "New Faculty", "role": "faculty"},
    )
    assert response.status_code == 201
    assert response.json()["username"] == "new.faculty"
    listed = client.get("/api/users", headers=headers(admin_token))
    assert listed.status_code == 200
    assert any(user["username"] == "new.faculty" for user in listed.json())


def test_non_admin_cannot_manage_users(client):
    student_token = login(client, "student", "student123")
    assert client.get("/api/users", headers=headers(student_token)).status_code == 403
    response = client.post(
        "/api/users",
        headers=headers(student_token),
        json={"username": "intruder", "password": "strongpass123", "name": "Intruder User", "role": "admin"},
    )
    assert response.status_code == 403


def test_duplicate_user_is_rejected(client):
    admin_token = login(client, "admin", "admin123")
    response = client.post(
        "/api/users",
        headers=headers(admin_token),
        json={"username": "student", "password": "strongpass123", "name": "Duplicate Student", "role": "student"},
    )
    assert response.status_code == 409


def test_logout_invalidates_session(client):
    token = login(client, "student", "student123")
    response = client.post("/api/logout", headers=headers(token))
    assert response.status_code == 200
    assert client.get("/api/me", headers=headers(token)).status_code == 401


def test_admin_can_view_student_analytics_overview(client):
    token = login(client, "admin", "admin123")
    response = client.get("/api/analytics/overview", headers=headers(token))
    assert response.status_code == 200
    data = response.json()
    assert data["student_count"] >= 5
    assert 0 <= data["average_attendance"] <= 100
    assert len(data["students"]) == data["student_count"]


def test_student_only_sees_own_analytics(client):
    token = login(client, "student", "student123")
    response = client.get("/api/analytics/overview", headers=headers(token))
    assert response.status_code == 200
    assert response.json()["student_count"] == 1
    assert response.json()["students"][0]["username"] == "student"
    assert client.get("/api/analytics/students/ananya", headers=headers(token)).status_code == 403


def test_faculty_can_update_student_metrics(client):
    token = login(client, "faculty", "faculty123")
    response = client.put(
        "/api/analytics/students/rahul",
        headers=headers(token),
        json={
            "full_name": "Rahul Verma",
            "section": "CSE-A",
            "attendance_present": 20,
            "attendance_total": 25,
            "assignments_done": 20,
            "assignments_total": 25,
            "marks": [80, 82, 84],
        },
    )
    assert response.status_code == 200, response.text
    assert response.json()["attendance_rate"] == 80
    assert response.json()["average_marks"] == 82


def test_student_cannot_update_metrics(client):
    token = login(client, "student", "student123")
    response = client.put(
        "/api/analytics/students/student",
        headers=headers(token),
        json={
            "full_name": "Demo Student",
            "section": "CSE-A",
            "attendance_present": 18,
            "attendance_total": 20,
            "assignments_done": 18,
            "assignments_total": 20,
            "marks": [78, 84, 81],
        },
    )
    assert response.status_code == 403


def test_study_plan_returns_actionable_recommendations(client):
    token = login(client, "student", "student123")
    response = client.get("/api/analytics/study-plan", headers=headers(token))
    assert response.status_code == 200
    assert response.json()["tasks"]
    assert any("priority" in task and "detail" in task for task in response.json()["tasks"])
