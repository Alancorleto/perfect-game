import os

# Environment variables must be set BEFORE importing any app module,
# because database.py creates the engine at module load time.
os.environ.setdefault("DATABASE_URL", "sqlite://")
os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-only-for-testing")
os.environ.setdefault("JWT_ALGORITHM", "HS256")

import pytest
from fastapi import status
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine
from sqlmodel.pool import StaticPool

from database import get_session
from main import app
from models.user import User
from routers.users import get_password_hash

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(name="session")
def session_fixture():
    """Creates an in-memory SQLite database for each test."""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


@pytest.fixture(name="client")
def client_fixture(session: Session):
    """Creates a TestClient that uses the test session instead of the production one."""

    def get_session_override():
        return session

    app.dependency_overrides[get_session] = get_session_override
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def create_user_in_db(
    session: Session,
    email: str = "user@example.com",
    password: str = "securepassword123",
    is_super_admin: bool = False,
) -> User:
    """Creates a user directly in the test database."""
    user = User(
        email=email,
        hashed_password=get_password_hash(password),
        is_super_admin=is_super_admin,
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


def get_auth_headers(client: TestClient, email: str, password: str) -> dict:
    """Logs in and returns Authorization headers with the access token."""
    response = client.post("/token", data={"username": email, "password": password})
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


# ---------------------------------------------------------------------------
# POST /users
# ---------------------------------------------------------------------------


def test_create_user(client: TestClient):
    response = client.post(
        "/users",
        json={"email": "test@example.com", "password": "securepassword123"},
    )
    data = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert data["email"] == "test@example.com"
    assert data["id"] is not None
    assert "password" not in data
    assert "hashed_password" not in data


def test_create_user_duplicate_email(session: Session, client: TestClient):
    create_user_in_db(session, email="duplicate@example.com")

    response = client.post(
        "/users",
        json={"email": "duplicate@example.com", "password": "anotherpassword123"},
    )

    assert response.status_code == status.HTTP_409_CONFLICT


def test_create_user_invalid_email(client: TestClient):
    response = client.post(
        "/users",
        json={"email": "not-an-email", "password": "securepassword123"},
    )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT


def test_create_user_password_too_short(client: TestClient):
    response = client.post(
        "/users",
        json={"email": "test@example.com", "password": "short"},
    )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT


# ---------------------------------------------------------------------------
# POST /token (login)
# ---------------------------------------------------------------------------


def test_login(session: Session, client: TestClient):
    create_user_in_db(session, email="login@example.com", password="mypassword123")

    response = client.post(
        "/token",
        data={"username": "login@example.com", "password": "mypassword123"},
    )
    data = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert data["access_token"] is not None
    assert data["token_type"] == "bearer"
    assert data["refresh_token"] is not None


def test_login_wrong_password(session: Session, client: TestClient):
    create_user_in_db(session, email="user@example.com", password="correctpassword")

    response = client.post(
        "/token",
        data={"username": "user@example.com", "password": "wrongpassword"},
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_login_nonexistent_user(client: TestClient):
    response = client.post(
        "/token",
        data={"username": "ghost@example.com", "password": "doesnotmatter"},
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


# ---------------------------------------------------------------------------
# POST /token/refresh
# ---------------------------------------------------------------------------


def test_refresh_token(session: Session, client: TestClient):
    create_user_in_db(session, email="refresh@example.com", password="mypassword123")

    login_response = client.post(
        "/token",
        data={"username": "refresh@example.com", "password": "mypassword123"},
    )
    refresh_token = login_response.json()["refresh_token"]

    response = client.post("/token/refresh", params={"refresh_token": refresh_token})
    data = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert data["access_token"] is not None
    assert data["token_type"] == "bearer"


def test_refresh_token_invalid(client: TestClient):
    response = client.post(
        "/token/refresh", params={"refresh_token": "totally-invalid-token"}
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_refresh_token_revoked(session: Session, client: TestClient):
    create_user_in_db(session, email="user@example.com", password="mypassword123")

    login_response = client.post(
        "/token",
        data={"username": "user@example.com", "password": "mypassword123"},
    )
    refresh_token = login_response.json()["refresh_token"]

    client.post("/token/revoke", params={"refresh_token": refresh_token})

    response = client.post("/token/refresh", params={"refresh_token": refresh_token})

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


# ---------------------------------------------------------------------------
# POST /token/revoke
# ---------------------------------------------------------------------------


def test_revoke_token(session: Session, client: TestClient):
    create_user_in_db(session, email="user@example.com", password="mypassword123")

    login_response = client.post(
        "/token",
        data={"username": "user@example.com", "password": "mypassword123"},
    )
    refresh_token = login_response.json()["refresh_token"]

    response = client.post("/token/revoke", params={"refresh_token": refresh_token})

    assert response.status_code == status.HTTP_204_NO_CONTENT


def test_revoke_token_nonexistent(client: TestClient):
    """Revoking a non-existent token should not raise an error."""
    response = client.post(
        "/token/revoke", params={"refresh_token": "nonexistent-token"}
    )

    assert response.status_code == status.HTTP_204_NO_CONTENT


# ---------------------------------------------------------------------------
# GET /users/me
# ---------------------------------------------------------------------------


def test_get_me(session: Session, client: TestClient):
    create_user_in_db(session, email="me@example.com", password="mypassword123")
    headers = get_auth_headers(client, "me@example.com", "mypassword123")

    response = client.get("/users/me", headers=headers)
    data = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert data["email"] == "me@example.com"
    assert data["id"] is not None


def test_get_me_unauthenticated(client: TestClient):
    response = client.get("/users/me")

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


# ---------------------------------------------------------------------------
# GET /users
# ---------------------------------------------------------------------------


def test_list_users(session: Session, client: TestClient):
    create_user_in_db(session, email="alice@example.com")
    create_user_in_db(session, email="bob@example.com")

    response = client.get("/users")
    data = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert len(data) == 2
    emails = [u["email"] for u in data]
    assert "alice@example.com" in emails
    assert "bob@example.com" in emails


def test_list_users_empty(client: TestClient):
    response = client.get("/users")

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == []


# ---------------------------------------------------------------------------
# GET /users/{user_id}
# ---------------------------------------------------------------------------


def test_get_user(session: Session, client: TestClient):
    user = create_user_in_db(session, email="target@example.com")

    response = client.get(f"/users/{user.id}")
    data = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert data["email"] == "target@example.com"
    assert data["id"] == str(user.id)


def test_get_user_not_found(client: TestClient):
    response = client.get("/users/00000000-0000-0000-0000-000000000000")

    assert response.status_code == status.HTTP_404_NOT_FOUND


# ---------------------------------------------------------------------------
# PATCH /users/{user_id}
# ---------------------------------------------------------------------------


def test_update_user(session: Session, client: TestClient):
    user = create_user_in_db(session, email="old@example.com", password="mypassword123")
    headers = get_auth_headers(client, "old@example.com", "mypassword123")

    response = client.patch(
        f"/users/{user.id}",
        json={"email": "new@example.com"},
        headers=headers,
    )
    data = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert data["email"] == "new@example.com"


def test_update_user_password(session: Session, client: TestClient):
    user = create_user_in_db(
        session, email="user@example.com", password="oldpassword123"
    )
    headers = get_auth_headers(client, "user@example.com", "oldpassword123")

    client.patch(
        f"/users/{user.id}",
        json={"password": "newpassword456"},
        headers=headers,
    )

    # Verify the new password works for a fresh login
    login_response = client.post(
        "/token",
        data={"username": "user@example.com", "password": "newpassword456"},
    )

    assert login_response.status_code == status.HTTP_200_OK


def test_update_user_not_found(session: Session, client: TestClient):
    # The 404 is returned before the authorization check, so any logged-in user works
    user = create_user_in_db(
        session, email="user@example.com", password="mypassword123"
    )
    headers = get_auth_headers(client, "user@example.com", "mypassword123")

    response = client.patch(
        "/users/00000000-0000-0000-0000-000000000000",
        json={"email": "x@example.com"},
        headers=headers,
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_update_user_unauthorized(session: Session, client: TestClient):
    target = create_user_in_db(session, email="target@example.com")
    create_user_in_db(session, email="attacker@example.com", password="mypassword123")
    headers = get_auth_headers(client, "attacker@example.com", "mypassword123")

    response = client.patch(
        f"/users/{target.id}",
        json={"email": "hacked@example.com"},
        headers=headers,
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_update_user_as_super_admin(session: Session, client: TestClient):
    target = create_user_in_db(session, email="target@example.com")
    create_user_in_db(
        session,
        email="admin@example.com",
        password="mypassword123",
        is_super_admin=True,
    )
    headers = get_auth_headers(client, "admin@example.com", "mypassword123")

    response = client.patch(
        f"/users/{target.id}",
        json={"email": "updated@example.com"},
        headers=headers,
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["email"] == "updated@example.com"


def test_update_user_email_already_registered(session: Session, client: TestClient):
    target = create_user_in_db(session, email="target@example.com")
    create_user_in_db(
        session,
        email="admin@example.com",
        password="mypassword123",
        is_super_admin=True,
    )
    headers = get_auth_headers(client, "admin@example.com", "mypassword123")

    response = client.patch(
        f"/users/{target.id}",
        json={"email": "admin@example.com"},
        headers=headers,
    )

    assert response.status_code == status.HTTP_409_CONFLICT


# ---------------------------------------------------------------------------
# DELETE /users/{user_id}
# ---------------------------------------------------------------------------


def test_delete_user(session: Session, client: TestClient):
    user = create_user_in_db(
        session, email="delete_me@example.com", password="mypassword123"
    )
    headers = get_auth_headers(client, "delete_me@example.com", "mypassword123")

    response = client.delete(f"/users/{user.id}", headers=headers)

    assert response.status_code == status.HTTP_204_NO_CONTENT

    # Confirm the user no longer exists
    get_response = client.get(f"/users/{user.id}")
    assert get_response.status_code == status.HTTP_404_NOT_FOUND


def test_delete_user_not_found(session: Session, client: TestClient):
    # The 404 is returned before the authorization check, so any logged-in user works
    user = create_user_in_db(
        session, email="user@example.com", password="mypassword123"
    )
    headers = get_auth_headers(client, "user@example.com", "mypassword123")

    response = client.delete(
        "/users/00000000-0000-0000-0000-000000000000", headers=headers
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_delete_user_unauthorized(session: Session, client: TestClient):
    target = create_user_in_db(session, email="target@example.com")
    create_user_in_db(session, email="attacker@example.com", password="mypassword123")
    headers = get_auth_headers(client, "attacker@example.com", "mypassword123")

    response = client.delete(f"/users/{target.id}", headers=headers)

    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_delete_user_as_super_admin(session: Session, client: TestClient):
    target = create_user_in_db(session, email="target@example.com")
    create_user_in_db(
        session,
        email="admin@example.com",
        password="mypassword123",
        is_super_admin=True,
    )
    headers = get_auth_headers(client, "admin@example.com", "mypassword123")

    response = client.delete(f"/users/{target.id}", headers=headers)

    assert response.status_code == status.HTTP_204_NO_CONTENT
