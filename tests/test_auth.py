import uuid

from fastapi.testclient import TestClient

from src.app import _db_connect, _initialize_db, app


_initialize_db()
client = TestClient(app)


def _cleanup_user(email: str) -> None:
    with _db_connect() as conn:
        row = conn.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone()
        if row is None:
            return

        user_id = int(row["id"])
        conn.execute("DELETE FROM sessions WHERE user_id = ?", (user_id,))
        conn.execute("DELETE FROM users WHERE id = ?", (user_id,))
        conn.commit()


def test_register_and_login_flow():
    email = f"student-{uuid.uuid4().hex[:8]}@mergington.edu"
    password = "StrongPass123!"

    register_response = client.post(
        "/auth/register",
        json={"email": email, "password": password},
    )
    assert register_response.status_code == 200
    register_data = register_response.json()
    assert register_data["user"]["role"] == "student"
    assert register_data["token"]

    login_response = client.post(
        "/auth/login",
        json={"email": email, "password": password},
    )
    assert login_response.status_code == 200
    login_data = login_response.json()
    assert login_data["token"]

    _cleanup_user(email)


def test_login_failure_with_wrong_password():
    email = f"student-{uuid.uuid4().hex[:8]}@mergington.edu"
    password = "StrongPass123!"

    register_response = client.post(
        "/auth/register",
        json={"email": email, "password": password},
    )
    assert register_response.status_code == 200

    bad_login = client.post(
        "/auth/login",
        json={"email": email, "password": "WrongPass123!"},
    )
    assert bad_login.status_code == 401

    _cleanup_user(email)


def test_admin_only_endpoint_rejects_student():
    email = f"student-{uuid.uuid4().hex[:8]}@mergington.edu"
    password = "StrongPass123!"

    register_response = client.post(
        "/auth/register",
        json={"email": email, "password": password},
    )
    assert register_response.status_code == 200
    token = register_response.json()["token"]

    users_response = client.get(
        "/admin/users",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert users_response.status_code == 403

    _cleanup_user(email)
