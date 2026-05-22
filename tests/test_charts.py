from fastapi import status
from fastapi.testclient import TestClient
from sqlmodel import Session

from models.chart import Mode
from tests.helpers import create_chart_in_db, create_user_in_db, get_auth_headers

# ---------------------------------------------------------------------------
# GET /charts/
# ---------------------------------------------------------------------------


def test_list_charts(session: Session, client: TestClient):
    user = create_user_in_db(
        session, email="user@example.com", password="mypassword123"
    )
    headers = get_auth_headers(client, "user@example.com", "mypassword123")
    create_chart_in_db(
        session,
        creator=user,
        song_name="Song A",
        mode=Mode.SINGLE,
        level=10,
    )
    create_chart_in_db(
        session,
        creator=user,
        song_name="Song B",
        mode=Mode.DOUBLE,
        level=15,
    )

    response = client.get("/charts/", headers=headers)
    data = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert len(data) == 2
    levels = [c["level"] for c in data]
    song_names = [c["song_name"] for c in data]
    assert 10 in levels
    assert 15 in levels
    assert "Song A" in song_names
    assert "Song B" in song_names


def test_list_charts_empty(session: Session, client: TestClient):
    create_user_in_db(session, email="user@example.com", password="mypassword123")
    headers = get_auth_headers(client, "user@example.com", "mypassword123")

    response = client.get("/charts/", headers=headers)

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == []


# ---------------------------------------------------------------------------
# GET /charts/{chart_id}
# ---------------------------------------------------------------------------


def test_get_chart(session: Session, client: TestClient):
    user = create_user_in_db(
        session, email="user@example.com", password="mypassword123"
    )
    headers = get_auth_headers(client, "user@example.com", "mypassword123")
    chart = create_chart_in_db(
        session,
        creator=user,
        song_name="My Song",
        mode=Mode.DOUBLE,
        level=18,
        player_count=2,
    )

    response = client.get(f"/charts/{chart.id}", headers=headers)
    data = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert data["id"] == str(chart.id)
    assert data["mode"] == "double"
    assert data["level"] == 18
    assert data["player_count"] == 2
    assert data["song_name"] == "My Song"


def test_get_chart_not_found(session: Session, client: TestClient):
    create_user_in_db(session, email="user@example.com", password="mypassword123")
    headers = get_auth_headers(client, "user@example.com", "mypassword123")

    response = client.get(
        "/charts/00000000-0000-0000-0000-000000000000", headers=headers
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND


# ---------------------------------------------------------------------------
# POST /charts/
# ---------------------------------------------------------------------------


def test_create_chart(session: Session, client: TestClient):
    create_user_in_db(session, email="user@example.com", password="mypassword123")
    headers = get_auth_headers(client, "user@example.com", "mypassword123")

    response = client.post(
        "/charts/",
        json={
            "song_name": "New Chart Song",
            "mode": "single_performance",
            "level": 20,
            "player_count": 1,
        },
        headers=headers,
    )
    data = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert data["id"] is not None
    assert data["mode"] == "single_performance"
    assert data["level"] == 20
    assert data["player_count"] == 1
    assert data["song_name"] == "New Chart Song"


def test_create_chart_with_defaults(session: Session, client: TestClient):
    create_user_in_db(session, email="user@example.com", password="mypassword123")
    headers = get_auth_headers(client, "user@example.com", "mypassword123")

    response = client.post(
        "/charts/", json={"song_name": "Default Chart Song"}, headers=headers
    )
    data = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert data["mode"] == "single"
    assert data["level"] == 1
    assert data["player_count"] == 1
    assert data["song_name"] == "Default Chart Song"


def test_create_chart_missing_song_id(session: Session, client: TestClient):
    create_user_in_db(session, email="user@example.com", password="mypassword123")
    headers = get_auth_headers(client, "user@example.com", "mypassword123")

    response = client.post("/charts/", json={"level": 10}, headers=headers)

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT


def test_create_chart_invalid_mode(session: Session, client: TestClient):
    create_user_in_db(session, email="user@example.com", password="mypassword123")
    headers = get_auth_headers(client, "user@example.com", "mypassword123")

    response = client.post(
        "/charts/",
        json={"song_name": "Invalid Mode Song", "mode": "invalid", "level": 10},
        headers=headers,
    )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT


def test_create_chart_invalid_level(session: Session, client: TestClient):
    create_user_in_db(session, email="user@example.com", password="mypassword123")
    headers = get_auth_headers(client, "user@example.com", "mypassword123")

    response = client.post(
        "/charts/",
        json={"song_name": "Invalid Level Song", "level": 0},
        headers=headers,
    )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT


def test_create_chart_invalid_player_count(session: Session, client: TestClient):
    create_user_in_db(session, email="user@example.com", password="mypassword123")
    headers = get_auth_headers(client, "user@example.com", "mypassword123")

    response = client.post(
        "/charts/",
        json={"song_name": "Invalid Player Count Song", "player_count": 0},
        headers=headers,
    )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT


def test_create_chart_with_invalid_level(session: Session, client: TestClient):
    """Test creating a chart with an invalid level (e.g., negative or too high)."""
    create_user_in_db(session, email="user@example.com", password="mypassword123")
    headers = get_auth_headers(client, "user@example.com", "mypassword123")

    response = client.post(
        "/charts/",
        json={"song_name": "Invalid Level Song", "mode": "single", "level": -1},
        headers=headers,
    )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT


# ---------------------------------------------------------------------------
# PATCH /charts/{chart_id}
# ---------------------------------------------------------------------------


def test_update_chart(session: Session, client: TestClient):
    user = create_user_in_db(
        session, email="user@example.com", password="mypassword123"
    )
    headers = get_auth_headers(client, "user@example.com", "mypassword123")
    chart = create_chart_in_db(
        session,
        creator=user,
        song_name="Update Song",
        mode=Mode.SINGLE,
        level=8,
    )

    response = client.patch(
        f"/charts/{chart.id}",
        json={"mode": "double_performance", "level": 17, "player_count": 2},
        headers=headers,
    )
    data = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert data["mode"] == "double_performance"
    assert data["level"] == 17
    assert data["player_count"] == 2
    assert data["song_name"] == "Update Song"


def test_update_chart_partial(session: Session, client: TestClient):
    user = create_user_in_db(
        session, email="user@example.com", password="mypassword123"
    )
    headers = get_auth_headers(client, "user@example.com", "mypassword123")
    chart = create_chart_in_db(
        session,
        creator=user,
        song_name="Partial Update Song",
        mode=Mode.COOP,
        level=12,
        player_count=3,
    )

    response = client.patch(f"/charts/{chart.id}", json={"level": 16}, headers=headers)
    data = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert data["mode"] == "coop"
    assert data["level"] == 16
    assert data["player_count"] == 3


def test_update_chart_not_found(session: Session, client: TestClient):
    create_user_in_db(session, email="user@example.com", password="mypassword123")
    headers = get_auth_headers(client, "user@example.com", "mypassword123")

    response = client.patch(
        "/charts/00000000-0000-0000-0000-000000000000",
        json={"level": 12},
        headers=headers,
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_update_chart_invalid_mode(session: Session, client: TestClient):
    user = create_user_in_db(
        session, email="user@example.com", password="mypassword123"
    )
    headers = get_auth_headers(client, "user@example.com", "mypassword123")
    chart = create_chart_in_db(session, creator=user, song_name="Invalid Update Song")

    response = client.patch(
        f"/charts/{chart.id}", json={"mode": "invalid"}, headers=headers
    )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT


# ---------------------------------------------------------------------------
# DELETE /charts/{chart_id}
# ---------------------------------------------------------------------------


def test_delete_chart(session: Session, client: TestClient):
    user = create_user_in_db(
        session,
        email="admin@example.com",
        password="mypassword123",
        is_super_admin=True,
    )
    headers = get_auth_headers(client, "admin@example.com", "mypassword123")
    chart = create_chart_in_db(session, creator=user, song_name="Delete Chart")
    chart_id = chart.id

    response = client.delete(f"/charts/{chart_id}", headers=headers)
    assert response.status_code == status.HTTP_204_NO_CONTENT

    get_response = client.get(f"/charts/{chart_id}", headers=headers)
    assert get_response.status_code == status.HTTP_404_NOT_FOUND


def test_delete_chart_not_found(session: Session, client: TestClient):
    create_user_in_db(
        session,
        email="admin@example.com",
        password="mypassword123",
        is_super_admin=True,
    )
    headers = get_auth_headers(client, "admin@example.com", "mypassword123")

    response = client.delete(
        "/charts/00000000-0000-0000-0000-000000000000", headers=headers
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND
