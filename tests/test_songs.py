from unittest.mock import AsyncMock, patch

from fastapi import status
from fastapi.testclient import TestClient
from sqlmodel import Session

from tests.helpers import create_song_in_db

# ---------------------------------------------------------------------------
# GET /songs/
# ---------------------------------------------------------------------------


def test_list_songs(session: Session, client: TestClient):
    create_song_in_db(session, name="Song A")
    create_song_in_db(session, name="Song B")

    response = client.get("/songs/")
    data = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert len(data) == 2
    names = [s["name"] for s in data]
    assert "Song A" in names
    assert "Song B" in names


def test_list_songs_empty(client: TestClient):
    response = client.get("/songs/")

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == []


# ---------------------------------------------------------------------------
# GET /songs/{song_id}
# ---------------------------------------------------------------------------


def test_get_song(session: Session, client: TestClient):
    song = create_song_in_db(
        session, name="My Song", title_url="https://example.com/title.png"
    )

    response = client.get(f"/songs/{song.id}")
    data = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert data["name"] == "My Song"
    assert data["title_url"] == "https://example.com/title.png"
    assert data["id"] == str(song.id)


def test_get_song_not_found(client: TestClient):
    response = client.get("/songs/00000000-0000-0000-0000-000000000000")

    assert response.status_code == status.HTTP_404_NOT_FOUND


# ---------------------------------------------------------------------------
# POST /songs/
# ---------------------------------------------------------------------------


def test_create_song(client: TestClient):
    response = client.post(
        "/songs/",
        json={"name": "New Song", "title_url": "https://example.com/new-title.png"},
    )
    data = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert data["name"] == "New Song"
    assert data["title_url"] == "https://example.com/new-title.png"
    assert data["id"] is not None


def test_create_song_without_title_url(client: TestClient):
    response = client.post("/songs/", json={"name": "New Song"})
    data = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert data["name"] == "New Song"
    assert data["title_url"] is None
    assert data["id"] is not None


def test_create_song_missing_name(client: TestClient):
    response = client.post("/songs/", json={"title_url": "https://example.com/a.png"})

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT


# ---------------------------------------------------------------------------
# PATCH /songs/{song_id}
# ---------------------------------------------------------------------------


def test_update_song(session: Session, client: TestClient):
    song = create_song_in_db(session, name="Old Song")

    response = client.patch(
        f"/songs/{song.id}",
        json={"name": "Updated Song", "title_url": "https://example.com/title.png"},
    )
    data = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert data["name"] == "Updated Song"
    assert data["title_url"] == "https://example.com/title.png"


def test_update_song_partial(session: Session, client: TestClient):
    song = create_song_in_db(
        session, name="Old Song", title_url="https://example.com/old-title.png"
    )

    response = client.patch(f"/songs/{song.id}", json={"name": "Renamed Song"})
    data = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert data["name"] == "Renamed Song"
    assert data["title_url"] == "https://example.com/old-title.png"


def test_update_song_not_found(client: TestClient):
    response = client.patch(
        "/songs/00000000-0000-0000-0000-000000000000",
        json={"name": "Updated Song"},
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND


# ---------------------------------------------------------------------------
# DELETE /songs/{song_id}
# ---------------------------------------------------------------------------


def test_delete_song(session: Session, client: TestClient):
    song = create_song_in_db(session, name="To Delete")

    response = client.delete(f"/songs/{song.id}")

    assert response.status_code == status.HTTP_204_NO_CONTENT

    get_response = client.get(f"/songs/{song.id}")
    assert get_response.status_code == status.HTTP_404_NOT_FOUND


def test_delete_song_not_found(client: TestClient):
    response = client.delete("/songs/00000000-0000-0000-0000-000000000000")

    assert response.status_code == status.HTTP_404_NOT_FOUND


# ---------------------------------------------------------------------------
# POST /songs/{song_id}/title
# ---------------------------------------------------------------------------


def test_upload_song_title(session: Session, client: TestClient):
    song = create_song_in_db(session, name="Title Song")

    with patch(
        "routers.songs.upload_image",
        new=AsyncMock(return_value="https://example.com/song-title.png"),
    ):
        response = client.post(
            f"/songs/{song.id}/title",
            files={"title_file": ("title.png", b"fake image bytes", "image/png")},
        )

    data = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert data["title_url"] == "https://example.com/song-title.png"


def test_upload_song_title_not_found(client: TestClient):
    response = client.post(
        "/songs/00000000-0000-0000-0000-000000000000/title",
        files={"title_file": ("title.png", b"fake image bytes", "image/png")},
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND
