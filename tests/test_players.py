from unittest.mock import AsyncMock, patch

from fastapi import status
from fastapi.testclient import TestClient
from sqlmodel import Session

from tests.helpers import (
    create_event_in_db,
    create_player_in_db,
    create_user_in_db,
    get_auth_headers,
)

# ---------------------------------------------------------------------------
# GET /players/
# ---------------------------------------------------------------------------


def test_list_players(session: Session, client: TestClient):
    user_a = create_user_in_db(session, email="a@example.com")
    user_b = create_user_in_db(session, email="b@example.com")
    create_player_in_db(session, user=user_a, nickname="PlayerA", country_code="AR")
    create_player_in_db(session, user=user_b, nickname="PlayerB", country_code="BR")

    response = client.get("/players/")
    data = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert len(data) == 2
    nicknames = [p["nickname"] for p in data]
    assert "PlayerA" in nicknames
    assert "PlayerB" in nicknames


def test_list_players_filtered_by_country(session: Session, client: TestClient):
    user_a = create_user_in_db(session, email="a@example.com")
    user_b = create_user_in_db(session, email="b@example.com")
    create_player_in_db(session, user=user_a, nickname="PlayerA", country_code="AR")
    create_player_in_db(session, user=user_b, nickname="PlayerB", country_code="BR")

    response = client.get("/players/?country_code=ar")
    data = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert len(data) == 1
    assert data[0]["nickname"] == "PlayerA"
    assert data[0]["country_code"] == "AR"


def test_list_players_filtered_by_country_with_no_matches(
    session: Session, client: TestClient
):
    create_user_in_db(session, email="a@example.com")
    create_player_in_db(session, nickname="PlayerA", country_code="AR")

    response = client.get("/players/?country_code=br")
    data = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert data == []


def test_list_players_empty(client: TestClient):
    response = client.get("/players/")

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == []


# ---------------------------------------------------------------------------
# GET /players/{player_id}
# ---------------------------------------------------------------------------


def test_get_player(session: Session, client: TestClient):
    user = create_user_in_db(session, email="user@example.com")
    player = create_player_in_db(session, user=user, nickname="NickTest")

    response = client.get(f"/players/{player.id}")
    data = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert data["nickname"] == "NickTest"
    assert data["id"] == str(player.id)


def test_get_player_not_found(client: TestClient):
    response = client.get("/players/00000000-0000-0000-0000-000000000000")

    assert response.status_code == status.HTTP_404_NOT_FOUND


# ---------------------------------------------------------------------------
# POST /players/
# ---------------------------------------------------------------------------


def test_create_player(session: Session, client: TestClient):
    create_user_in_db(session, email="user@example.com", password="mypassword123")
    headers = get_auth_headers(client, "user@example.com", "mypassword123")

    response = client.post(
        "/players/",
        json={"nickname": "NewPlayer", "country_code": "AR"},
        headers=headers,
    )
    data = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert data["nickname"] == "NewPlayer"
    assert data["id"] is not None
    assert data["country_code"] == "AR"


def test_create_player_unauthenticated(client: TestClient):
    response = client.post(
        "/players/", json={"nickname": "NewPlayer", "country_code": "AR"}
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_create_player_already_has_player(session: Session, client: TestClient):
    user = create_user_in_db(
        session, email="user@example.com", password="mypassword123"
    )
    create_player_in_db(session, user=user, nickname="ExistingPlayer")
    headers = get_auth_headers(client, "user@example.com", "mypassword123")

    response = client.post(
        "/players/",
        json={"nickname": "AnotherPlayer", "country_code": "AR"},
        headers=headers,
    )

    assert response.status_code == status.HTTP_409_CONFLICT


# ---------------------------------------------------------------------------
# POST /players/guest/{event_id}
# ---------------------------------------------------------------------------


def test_create_guest_player(session: Session, client: TestClient):
    organizer = create_user_in_db(
        session, email="organizer@example.com", password="mypassword123"
    )
    event = create_event_in_db(session, organizer=organizer)
    headers = get_auth_headers(client, "organizer@example.com", "mypassword123")

    response = client.post(
        f"/players/guest/{event.id}",
        json={"nickname": "GuestPlayer", "country_code": "AR"},
        headers=headers,
    )
    data = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert data["nickname"] == "GuestPlayer"
    assert data["id"] is not None
    assert data["country_code"] == "AR"


def test_create_guest_player_event_not_found(session: Session, client: TestClient):
    create_user_in_db(session, email="user@example.com", password="mypassword123")
    headers = get_auth_headers(client, "user@example.com", "mypassword123")

    response = client.post(
        "/players/guest/00000000-0000-0000-0000-000000000000",
        json={"nickname": "GuestPlayer", "country_code": "AR"},
        headers=headers,
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_create_guest_player_not_organizer(session: Session, client: TestClient):
    create_user_in_db(session, email="user@example.com", password="mypassword123")
    event = create_event_in_db(session)
    headers = get_auth_headers(client, "user@example.com", "mypassword123")

    response = client.post(
        f"/players/guest/{event.id}",
        json={"nickname": "GuestPlayer", "country_code": "AR"},
        headers=headers,
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_create_guest_player_unauthenticated(session: Session, client: TestClient):
    event = create_event_in_db(session)

    response = client.post(
        f"/players/guest/{event.id}",
        json={"nickname": "GuestPlayer", "country_code": "AR"},
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


# ---------------------------------------------------------------------------
# PATCH /players/{player_id}
# ---------------------------------------------------------------------------


def test_update_player(session: Session, client: TestClient):
    user = create_user_in_db(
        session, email="user@example.com", password="mypassword123"
    )
    player = create_player_in_db(session, user=user, nickname="OldNick")
    headers = get_auth_headers(client, "user@example.com", "mypassword123")

    response = client.patch(
        f"/players/{player.id}",
        json={"nickname": "NewNick"},
        headers=headers,
    )
    data = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert data["nickname"] == "NewNick"


def test_update_player_not_found(session: Session, client: TestClient):
    create_user_in_db(session, email="user@example.com", password="mypassword123")
    headers = get_auth_headers(client, "user@example.com", "mypassword123")

    response = client.patch(
        "/players/00000000-0000-0000-0000-000000000000",
        json={"nickname": "NewNick"},
        headers=headers,
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_update_player_unauthorized(session: Session, client: TestClient):
    owner = create_user_in_db(session, email="owner@example.com")
    create_user_in_db(session, email="attacker@example.com", password="mypassword123")
    player = create_player_in_db(session, user=owner, nickname="OwnersPlayer")
    headers = get_auth_headers(client, "attacker@example.com", "mypassword123")

    response = client.patch(
        f"/players/{player.id}",
        json={"nickname": "Hacked"},
        headers=headers,
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_update_player_as_super_admin(session: Session, client: TestClient):
    owner = create_user_in_db(session, email="owner@example.com")
    create_user_in_db(
        session,
        email="admin@example.com",
        password="mypassword123",
        is_super_admin=True,
    )
    player = create_player_in_db(session, user=owner, nickname="OldNick")
    headers = get_auth_headers(client, "admin@example.com", "mypassword123")

    response = client.patch(
        f"/players/{player.id}",
        json={"nickname": "AdminUpdated"},
        headers=headers,
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["nickname"] == "AdminUpdated"


def test_update_player_as_event_organizer(session: Session, client: TestClient):
    """An event organizer can update a guest player of their event."""
    organizer = create_user_in_db(
        session, email="organizer@example.com", password="mypassword123"
    )
    event = create_event_in_db(session, organizer=organizer)
    guest_player = create_player_in_db(session, guest_event=event, nickname="GuestNick")
    headers = get_auth_headers(client, "organizer@example.com", "mypassword123")

    response = client.patch(
        f"/players/{guest_player.id}",
        json={"nickname": "UpdatedGuestNick"},
        headers=headers,
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["nickname"] == "UpdatedGuestNick"


def test_update_player_unauthenticated(session: Session, client: TestClient):
    user = create_user_in_db(session, email="user@example.com")
    player = create_player_in_db(session, user=user, nickname="SomePlayer")

    response = client.patch(f"/players/{player.id}", json={"nickname": "NewNick"})

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


# ---------------------------------------------------------------------------
# DELETE /players/{player_id}
# ---------------------------------------------------------------------------


def test_delete_player(session: Session, client: TestClient):
    user = create_user_in_db(
        session, email="user@example.com", password="mypassword123"
    )
    player = create_player_in_db(session, user=user, nickname="ToDelete")
    headers = get_auth_headers(client, "user@example.com", "mypassword123")

    response = client.delete(f"/players/{player.id}", headers=headers)

    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_delete_player_not_found(session: Session, client: TestClient):
    create_user_in_db(session, email="user@example.com", password="mypassword123")
    headers = get_auth_headers(client, "user@example.com", "mypassword123")

    response = client.delete(
        "/players/00000000-0000-0000-0000-000000000000", headers=headers
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_delete_player_unauthorized(session: Session, client: TestClient):
    owner = create_user_in_db(session, email="owner@example.com")
    create_user_in_db(session, email="attacker@example.com", password="mypassword123")
    player = create_player_in_db(session, user=owner, nickname="OwnersPlayer")
    headers = get_auth_headers(client, "attacker@example.com", "mypassword123")

    response = client.delete(f"/players/{player.id}", headers=headers)

    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_delete_player_as_super_admin(session: Session, client: TestClient):
    owner = create_user_in_db(session, email="owner@example.com")
    create_user_in_db(
        session,
        email="admin@example.com",
        password="mypassword123",
        is_super_admin=True,
    )
    player = create_player_in_db(session, user=owner, nickname="ToDelete")
    headers = get_auth_headers(client, "admin@example.com", "mypassword123")

    response = client.delete(f"/players/{player.id}", headers=headers)

    assert response.status_code == status.HTTP_204_NO_CONTENT


def test_delete_player_unauthenticated(session: Session, client: TestClient):
    user = create_user_in_db(session, email="user@example.com")
    player = create_player_in_db(session, user=user, nickname="SomePlayer")

    response = client.delete(f"/players/{player.id}")

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_delete_user_set_null(session: Session, client: TestClient):
    create_user_in_db(
        session,
        email="admin@example.com",
        password="mypassword123",
        is_super_admin=True,
    )
    headers = get_auth_headers(client, "admin@example.com", "mypassword123")

    user = create_user_in_db(
        session, email="user@example.com", password="mypassword123"
    )
    player = create_player_in_db(session, user=user, nickname="SomePlayer")

    response = client.delete(f"/users/{user.id}", headers=headers)

    assert response.status_code == status.HTTP_204_NO_CONTENT

    response = client.get(f"/players/{player.id}")
    data = response.json()
    assert data["user_id"] is None


# ---------------------------------------------------------------------------
# POST /players/{player_id}/profile_picture
# ---------------------------------------------------------------------------


def test_upload_profile_picture(session: Session, client: TestClient):
    user = create_user_in_db(
        session, email="user@example.com", password="mypassword123"
    )
    player = create_player_in_db(session, user=user, nickname="PicPlayer")
    headers = get_auth_headers(client, "user@example.com", "mypassword123")

    with patch(
        "routers.players.upload_image",
        new=AsyncMock(return_value="https://example.com/profile.png"),
    ):
        response = client.post(
            f"/players/{player.id}/profile_picture",
            files={"profile_picture": ("photo.png", b"fake image bytes", "image/png")},
            headers=headers,
        )

    data = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert data["profile_picture_url"] == "https://example.com/profile.png"


def test_upload_profile_picture_not_found(session: Session, client: TestClient):
    create_user_in_db(session, email="user@example.com", password="mypassword123")
    headers = get_auth_headers(client, "user@example.com", "mypassword123")

    response = client.post(
        "/players/00000000-0000-0000-0000-000000000000/profile_picture",
        files={"profile_picture": ("photo.png", b"fake image bytes", "image/png")},
        headers=headers,
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_upload_profile_picture_unauthorized(session: Session, client: TestClient):
    owner = create_user_in_db(session, email="owner@example.com")
    create_user_in_db(session, email="attacker@example.com", password="mypassword123")
    player = create_player_in_db(session, user=owner, nickname="PicPlayer")
    headers = get_auth_headers(client, "attacker@example.com", "mypassword123")

    response = client.post(
        f"/players/{player.id}/profile_picture",
        files={"profile_picture": ("photo.png", b"fake image bytes", "image/png")},
        headers=headers,
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_upload_profile_picture_unauthenticated(session: Session, client: TestClient):
    user = create_user_in_db(session, email="user@example.com")
    player = create_player_in_db(session, user=user, nickname="PicPlayer")

    response = client.post(
        f"/players/{player.id}/profile_picture",
        files={"profile_picture": ("photo.png", b"fake image bytes", "image/png")},
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
