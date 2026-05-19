from fastapi import status
from fastapi.testclient import TestClient
from sqlmodel import Session

from models.chart import Chart, Mode
from tests.helpers import create_chart_in_db, create_song_in_db

# ---------------------------------------------------------------------------
# GET /charts/
# ---------------------------------------------------------------------------


def test_list_charts(session: Session, client: TestClient):
    song_a = create_song_in_db(session, name="Song A")
    song_b = create_song_in_db(session, name="Song B")
    create_chart_in_db(session, song=song_a, mode=Mode.SINGLE, level=10)
    create_chart_in_db(session, song=song_b, mode=Mode.DOUBLE, level=15)

    response = client.get("/charts/")
    data = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert len(data) == 2
    levels = [c["level"] for c in data]
    song_names = [c["song"]["name"] for c in data]
    assert 10 in levels
    assert 15 in levels
    assert "Song A" in song_names
    assert "Song B" in song_names


def test_list_charts_empty(client: TestClient):
    response = client.get("/charts/")

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == []


# ---------------------------------------------------------------------------
# GET /charts/{chart_id}
# ---------------------------------------------------------------------------


def test_get_chart(session: Session, client: TestClient):
    song = create_song_in_db(session, name="My Song")
    chart = create_chart_in_db(
        session, song=song, mode=Mode.DOUBLE, level=18, player_count=2
    )

    response = client.get(f"/charts/{chart.id}")
    data = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert data["id"] == str(chart.id)
    assert data["mode"] == "double"
    assert data["level"] == 18
    assert data["player_count"] == 2
    assert data["song"]["id"] == str(song.id)
    assert data["song"]["name"] == "My Song"


def test_get_chart_not_found(client: TestClient):
    response = client.get("/charts/00000000-0000-0000-0000-000000000000")

    assert response.status_code == status.HTTP_404_NOT_FOUND


# ---------------------------------------------------------------------------
# POST /charts/
# ---------------------------------------------------------------------------


def test_create_chart(session: Session, client: TestClient):
    song = create_song_in_db(session, name="New Chart Song")

    response = client.post(
        "/charts/",
        json={
            "song_id": str(song.id),
            "mode": "single_performance",
            "level": 20,
            "player_count": 1,
        },
    )
    data = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert data["id"] is not None
    assert data["mode"] == "single_performance"
    assert data["level"] == 20
    assert data["player_count"] == 1
    assert data["song"]["id"] == str(song.id)
    assert data["song"]["name"] == "New Chart Song"


def test_create_chart_with_defaults(session: Session, client: TestClient):
    song = create_song_in_db(session, name="Default Chart Song")

    response = client.post("/charts/", json={"song_id": str(song.id)})
    data = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert data["mode"] == "single"
    assert data["level"] == 1
    assert data["player_count"] == 1
    assert data["song"]["id"] == str(song.id)


def test_create_chart_missing_song_id(client: TestClient):
    response = client.post("/charts/", json={"level": 10})

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT


def test_create_chart_invalid_mode(session: Session, client: TestClient):
    song = create_song_in_db(session, name="Invalid Mode Song")

    response = client.post(
        "/charts/",
        json={"song_id": str(song.id), "mode": "invalid", "level": 10},
    )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT


def test_create_chart_invalid_level(session: Session, client: TestClient):
    song = create_song_in_db(session, name="Invalid Level Song")

    response = client.post(
        "/charts/",
        json={"song_id": str(song.id), "level": 0},
    )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT


def test_create_chart_invalid_player_count(session: Session, client: TestClient):
    song = create_song_in_db(session, name="Invalid Player Count Song")

    response = client.post(
        "/charts/",
        json={"song_id": str(song.id), "player_count": 0},
    )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT


def test_create_chart_with_invalid_level(session: Session, client: TestClient):
    """Test creating a chart with an invalid level (e.g., negative or too high)."""
    song_response = client.post("/songs/", json={"name": "Test Song"})
    song_id = song_response.json()["id"]

    response = client.post(
        "/charts/",
        json={"song_id": song_id, "mode": "single", "level": -1},
    )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT


# ---------------------------------------------------------------------------
# PATCH /charts/{chart_id}
# ---------------------------------------------------------------------------


def test_update_chart(session: Session, client: TestClient):
    song = create_song_in_db(session, name="Update Song")
    chart = create_chart_in_db(session, song=song, mode=Mode.SINGLE, level=8)

    response = client.patch(
        f"/charts/{chart.id}",
        json={"mode": "double_performance", "level": 17, "player_count": 2},
    )
    data = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert data["mode"] == "double_performance"
    assert data["level"] == 17
    assert data["player_count"] == 2
    assert data["song"]["id"] == str(song.id)


def test_update_chart_partial(session: Session, client: TestClient):
    song = create_song_in_db(session, name="Partial Update Song")
    chart = create_chart_in_db(
        session, song=song, mode=Mode.COOP, level=12, player_count=3
    )

    response = client.patch(f"/charts/{chart.id}", json={"level": 16})
    data = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert data["mode"] == "coop"
    assert data["level"] == 16
    assert data["player_count"] == 3


def test_update_chart_not_found(client: TestClient):
    response = client.patch(
        "/charts/00000000-0000-0000-0000-000000000000",
        json={"level": 12},
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_update_chart_invalid_mode(session: Session, client: TestClient):
    song = create_song_in_db(session, name="Invalid Update Song")
    chart = create_chart_in_db(session, song=song)

    response = client.patch(f"/charts/{chart.id}", json={"mode": "invalid"})

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT


# ---------------------------------------------------------------------------
# DELETE /charts/{chart_id}
# ---------------------------------------------------------------------------


def test_delete_chart_not_found(client: TestClient):
    response = client.delete("/charts/00000000-0000-0000-0000-000000000000")

    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_delete_song_cascade(session: Session, client: TestClient):
    song = create_song_in_db(session, name="Delete Song")
    chart = create_chart_in_db(session, song=song)
    chart_id = chart.id

    response = client.delete(f"/songs/{song.id}")
    assert response.status_code == status.HTTP_204_NO_CONTENT

    get_response = client.get(f"/charts/{chart_id}")
    assert get_response.status_code == status.HTTP_404_NOT_FOUND
