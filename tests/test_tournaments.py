import pytest
from fastapi import status
from fastapi.testclient import TestClient
from sqlmodel import Session

from models.round import RoundState
from tests.helpers import (
    add_organizer_to_tournament,
    create_category_in_db,
    create_player_in_db,
    create_round_in_db,
    create_tournament_in_db,
    create_user_in_db,
    get_auth_headers,
)

# ---------------------------------------------------------------------------
# GET /tournaments/
# ---------------------------------------------------------------------------


def test_list_tournaments(session: Session, client: TestClient):
    create_tournament_in_db(session, name="Tournament A")
    create_tournament_in_db(session, name="Tournament B")

    response = client.get("/tournaments/")
    data = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert len(data) == 2
    names = [t["name"] for t in data]
    assert "Tournament A" in names
    assert "Tournament B" in names


def test_list_tournaments_empty(client: TestClient):
    response = client.get("/tournaments/")

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == []


# ---------------------------------------------------------------------------
# GET /tournaments/{tournament_id}
# ---------------------------------------------------------------------------


def test_get_tournament(session: Session, client: TestClient):
    tournament = create_tournament_in_db(session, name="My Tournament")

    response = client.get(f"/tournaments/{tournament.id}")
    data = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert data["name"] == "My Tournament"
    assert data["id"] == str(tournament.id)


def test_get_tournament_not_found(client: TestClient):
    response = client.get("/tournaments/00000000-0000-0000-0000-000000000000")

    assert response.status_code == status.HTTP_404_NOT_FOUND


# ---------------------------------------------------------------------------
# POST /tournaments
# ---------------------------------------------------------------------------


def test_create_tournament(session: Session, client: TestClient):
    create_user_in_db(session, email="user@example.com", password="mypassword123")
    headers = get_auth_headers(client, "user@example.com", "mypassword123")

    response = client.post(
        "/tournaments/",
        json={"name": "New Tournament"},
        headers=headers,
    )
    data = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert data["name"] == "New Tournament"
    assert data["id"] is not None


def test_create_tournament_creator_becomes_organizer(
    session: Session, client: TestClient
):
    create_user_in_db(session, email="user@example.com", password="mypassword123")
    headers = get_auth_headers(client, "user@example.com", "mypassword123")

    create_response = client.post(
        "/tournaments/",
        json={"name": "New Tournament"},
        headers=headers,
    )
    tournament_id = create_response.json()["id"]

    # The creator should be able to update the tournament (only organizers can)
    update_response = client.patch(
        f"/tournaments/{tournament_id}",
        json={"name": "Updated Name"},
        headers=headers,
    )

    assert update_response.status_code == status.HTTP_200_OK


def test_create_tournament_unauthenticated(client: TestClient):
    response = client.post("/tournaments/", json={"name": "New Tournament"})

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_create_tournament_with_long_name(session: Session, client: TestClient):
    """Test creating a tournament with an excessively long name."""
    user = create_user_in_db(
        session, email="organizer@example.com", password="mypassword123"
    )
    headers = get_auth_headers(client, "organizer@example.com", "mypassword123")

    long_name = "T" * 300
    response = client.post(
        "/tournaments/",
        json={"name": long_name},
        headers=headers,
    )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT


def test_create_tournament_with_empty_name(session: Session, client: TestClient):
    """Test creating a tournament with an empty name."""
    user = create_user_in_db(
        session, email="organizer@example.com", password="mypassword123"
    )
    headers = get_auth_headers(client, "organizer@example.com", "mypassword123")

    response = client.post(
        "/tournaments/",
        json={"name": ""},
        headers=headers,
    )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT


# ---------------------------------------------------------------------------
# PATCH /tournaments/{tournament_id}
# ---------------------------------------------------------------------------


def test_update_tournament(session: Session, client: TestClient):
    organizer = create_user_in_db(
        session, email="organizer@example.com", password="mypassword123"
    )
    tournament = create_tournament_in_db(session, organizer=organizer)
    headers = get_auth_headers(client, "organizer@example.com", "mypassword123")

    response = client.patch(
        f"/tournaments/{tournament.id}",
        json={"name": "Updated Name"},
        headers=headers,
    )
    data = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert data["name"] == "Updated Name"


def test_update_tournament_not_found(session: Session, client: TestClient):
    create_user_in_db(session, email="user@example.com", password="mypassword123")
    headers = get_auth_headers(client, "user@example.com", "mypassword123")

    response = client.patch(
        "/tournaments/00000000-0000-0000-0000-000000000000",
        json={"name": "Updated Name"},
        headers=headers,
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_update_tournament_unauthorized(session: Session, client: TestClient):
    create_user_in_db(session, email="attacker@example.com", password="mypassword123")
    tournament = create_tournament_in_db(session)
    headers = get_auth_headers(client, "attacker@example.com", "mypassword123")

    response = client.patch(
        f"/tournaments/{tournament.id}",
        json={"name": "Hacked"},
        headers=headers,
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_update_tournament_as_super_admin(session: Session, client: TestClient):
    create_user_in_db(
        session,
        email="admin@example.com",
        password="mypassword123",
        is_super_admin=True,
    )
    tournament = create_tournament_in_db(session)
    headers = get_auth_headers(client, "admin@example.com", "mypassword123")

    response = client.patch(
        f"/tournaments/{tournament.id}",
        json={"name": "Admin Updated"},
        headers=headers,
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["name"] == "Admin Updated"


def test_update_tournament_unauthenticated(session: Session, client: TestClient):
    tournament = create_tournament_in_db(session)

    response = client.patch(
        f"/tournaments/{tournament.id}", json={"name": "Updated Name"}
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


# ---------------------------------------------------------------------------
# DELETE /tournaments/{tournament_id}
# ---------------------------------------------------------------------------


def test_delete_tournament_empty(session: Session, client: TestClient):
    organizer = create_user_in_db(
        session, email="organizer@example.com", password="mypassword123"
    )
    tournament = create_tournament_in_db(session, organizer=organizer)
    headers = get_auth_headers(client, "organizer@example.com", "mypassword123")

    response = client.delete(f"/tournaments/{tournament.id}", headers=headers)

    assert response.status_code == status.HTTP_204_NO_CONTENT

    get_response = client.get(f"/tournaments/{tournament.id}", headers=headers)
    assert get_response.status_code == status.HTTP_404_NOT_FOUND


def test_delete_tournament_with_empty_category_and_round(
    session: Session, client: TestClient
):
    organizer = create_user_in_db(
        session, email="organizer@example.com", password="mypassword123"
    )
    tournament = create_tournament_in_db(session, organizer=organizer)
    category = create_category_in_db(session, tournament=tournament)
    create_round_in_db(session, category=category)

    headers = get_auth_headers(client, "organizer@example.com", "mypassword123")

    response = client.delete(f"/tournaments/{tournament.id}", headers=headers)

    assert response.status_code == status.HTTP_204_NO_CONTENT

    get_response = client.get(f"/tournaments/{tournament.id}", headers=headers)
    assert get_response.status_code == status.HTTP_404_NOT_FOUND


def test_delete_tournament_with_started_round(session: Session, client: TestClient):
    organizer = create_user_in_db(
        session, email="organizer@example.com", password="mypassword123"
    )
    tournament = create_tournament_in_db(session, organizer=organizer)
    category = create_category_in_db(session, tournament=tournament)
    create_round_in_db(session, category=category, state=RoundState.IN_PROGRESS)
    headers = get_auth_headers(client, "organizer@example.com", "mypassword123")

    response = client.delete(f"/tournaments/{tournament.id}", headers=headers)
    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_delete_tournament_not_found(session: Session, client: TestClient):
    create_user_in_db(session, email="user@example.com", password="mypassword123")
    headers = get_auth_headers(client, "user@example.com", "mypassword123")

    response = client.delete(
        "/tournaments/00000000-0000-0000-0000-000000000000", headers=headers
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_delete_tournament_unauthorized(session: Session, client: TestClient):
    create_user_in_db(session, email="attacker@example.com", password="mypassword123")
    tournament = create_tournament_in_db(session)
    headers = get_auth_headers(client, "attacker@example.com", "mypassword123")

    response = client.delete(f"/tournaments/{tournament.id}", headers=headers)

    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_delete_tournament_as_super_admin(session: Session, client: TestClient):
    create_user_in_db(
        session,
        email="admin@example.com",
        password="mypassword123",
        is_super_admin=True,
    )
    tournament = create_tournament_in_db(session)
    headers = get_auth_headers(client, "admin@example.com", "mypassword123")

    response = client.delete(f"/tournaments/{tournament.id}", headers=headers)

    assert response.status_code == status.HTTP_204_NO_CONTENT


def test_delete_tournament_unauthenticated(session: Session, client: TestClient):
    tournament = create_tournament_in_db(session)

    response = client.delete(f"/tournaments/{tournament.id}")

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


# ---------------------------------------------------------------------------
# GET /tournaments/{tournament_id}/categories
# ---------------------------------------------------------------------------


def test_list_tournament_categories_empty(session: Session, client: TestClient):
    tournament = create_tournament_in_db(session)

    response = client.get(f"/tournaments/{tournament.id}/categories")

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == []


def test_list_tournament_categories_not_found(client: TestClient):
    response = client.get(
        "/tournaments/00000000-0000-0000-0000-000000000000/categories"
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND


# ---------------------------------------------------------------------------
# GET /tournaments/{tournament_id}/organizers
# ---------------------------------------------------------------------------


def test_list_tournament_organizers(session: Session, client: TestClient):
    organizer = create_user_in_db(session, email="organizer@example.com")
    create_player_in_db(session, user=organizer, nickname="OrganizerPlayer")
    tournament = create_tournament_in_db(session, organizer=organizer)

    response = client.get(f"/tournaments/{tournament.id}/organizers")
    data = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert len(data) == 1
    assert data[0]["nickname"] == "OrganizerPlayer"


def test_list_tournament_organizers_without_player_profile(
    session: Session, client: TestClient
):
    """Organizers without a player profile are excluded from the response."""
    organizer = create_user_in_db(session, email="organizer@example.com")
    tournament = create_tournament_in_db(session, organizer=organizer)

    response = client.get(f"/tournaments/{tournament.id}/organizers")

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == []


def test_list_tournament_organizers_not_found(client: TestClient):
    response = client.get(
        "/tournaments/00000000-0000-0000-0000-000000000000/organizers"
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND


# ---------------------------------------------------------------------------
# POST /tournaments/{tournament_id}/organizers/{player_id}
# ---------------------------------------------------------------------------


def test_add_organizer(session: Session, client: TestClient):
    organizer = create_user_in_db(
        session, email="organizer@example.com", password="mypassword123"
    )
    tournament = create_tournament_in_db(session, organizer=organizer)
    headers = get_auth_headers(client, "organizer@example.com", "mypassword123")

    new_user = create_user_in_db(session, email="new@example.com")
    new_player = create_player_in_db(session, user=new_user, nickname="NewOrganizer")

    response = client.post(
        f"/tournaments/{tournament.id}/organizers/{new_player.id}",
        headers=headers,
    )
    data = response.json()

    assert response.status_code == status.HTTP_200_OK
    nicknames = [p["nickname"] for p in data]
    assert "NewOrganizer" in nicknames


def test_add_organizer_tournament_not_found(session: Session, client: TestClient):
    organizer = create_user_in_db(
        session, email="organizer@example.com", password="mypassword123"
    )
    player = create_player_in_db(session, user=organizer, nickname="SomePlayer")
    headers = get_auth_headers(client, "organizer@example.com", "mypassword123")

    response = client.post(
        f"/tournaments/00000000-0000-0000-0000-000000000000/organizers/{player.id}",
        headers=headers,
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_add_organizer_unauthorized(session: Session, client: TestClient):
    create_user_in_db(session, email="attacker@example.com", password="mypassword123")
    tournament = create_tournament_in_db(session)
    new_user = create_user_in_db(session, email="new@example.com")
    new_player = create_player_in_db(session, user=new_user, nickname="NewOrganizer")
    headers = get_auth_headers(client, "attacker@example.com", "mypassword123")

    response = client.post(
        f"/tournaments/{tournament.id}/organizers/{new_player.id}",
        headers=headers,
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_add_organizer_player_not_found(session: Session, client: TestClient):
    organizer = create_user_in_db(
        session, email="organizer@example.com", password="mypassword123"
    )
    tournament = create_tournament_in_db(session, organizer=organizer)
    headers = get_auth_headers(client, "organizer@example.com", "mypassword123")

    response = client.post(
        f"/tournaments/{tournament.id}/organizers/00000000-0000-0000-0000-000000000000",
        headers=headers,
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_add_organizer_player_has_no_user(session: Session, client: TestClient):
    """A guest player (no user account) cannot be added as organizer."""
    organizer = create_user_in_db(
        session, email="organizer@example.com", password="mypassword123"
    )
    tournament = create_tournament_in_db(session, organizer=organizer)
    guest_player = create_player_in_db(
        session, guest_tournament=tournament, nickname="GuestPlayer"
    )
    headers = get_auth_headers(client, "organizer@example.com", "mypassword123")

    response = client.post(
        f"/tournaments/{tournament.id}/organizers/{guest_player.id}",
        headers=headers,
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST


def test_add_organizer_already_organizer(session: Session, client: TestClient):
    organizer = create_user_in_db(
        session, email="organizer@example.com", password="mypassword123"
    )
    tournament = create_tournament_in_db(session, organizer=organizer)
    organizer_player = create_player_in_db(
        session, user=organizer, nickname="OrganizerPlayer"
    )
    headers = get_auth_headers(client, "organizer@example.com", "mypassword123")

    response = client.post(
        f"/tournaments/{tournament.id}/organizers/{organizer_player.id}",
        headers=headers,
    )

    assert response.status_code == status.HTTP_409_CONFLICT


def test_add_organizer_unauthenticated(session: Session, client: TestClient):
    tournament = create_tournament_in_db(session)
    user = create_user_in_db(session, email="user@example.com")
    player = create_player_in_db(session, user=user, nickname="SomePlayer")

    response = client.post(
        f"/tournaments/{tournament.id}/organizers/{player.id}",
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


# ---------------------------------------------------------------------------
# DELETE /tournaments/{tournament_id}/organizers/{player_id}
# ---------------------------------------------------------------------------


def test_remove_organizer(session: Session, client: TestClient):
    organizer = create_user_in_db(
        session, email="organizer@example.com", password="mypassword123"
    )
    tournament = create_tournament_in_db(session, organizer=organizer)
    headers = get_auth_headers(client, "organizer@example.com", "mypassword123")

    # Add a second organizer (needed so the first can be removed)
    second_user = create_user_in_db(session, email="second@example.com")
    second_player = create_player_in_db(
        session, user=second_user, nickname="SecondOrganizer"
    )
    add_organizer_to_tournament(session, tournament, second_user)

    response = client.delete(
        f"/tournaments/{tournament.id}/organizers/{second_player.id}",
        headers=headers,
    )
    data = response.json()

    assert response.status_code == status.HTTP_200_OK
    nicknames = [p["nickname"] for p in data]
    assert "SecondOrganizer" not in nicknames


def test_remove_organizer_tournament_not_found(session: Session, client: TestClient):
    organizer = create_user_in_db(
        session, email="organizer@example.com", password="mypassword123"
    )
    player = create_player_in_db(session, user=organizer, nickname="SomePlayer")
    headers = get_auth_headers(client, "organizer@example.com", "mypassword123")

    response = client.delete(
        f"/tournaments/00000000-0000-0000-0000-000000000000/organizers/{player.id}",
        headers=headers,
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_remove_organizer_unauthorized(session: Session, client: TestClient):
    create_user_in_db(session, email="attacker@example.com", password="mypassword123")
    tournament = create_tournament_in_db(session)
    user = create_user_in_db(session, email="user@example.com")
    player = create_player_in_db(session, user=user, nickname="SomePlayer")
    headers = get_auth_headers(client, "attacker@example.com", "mypassword123")

    response = client.delete(
        f"/tournaments/{tournament.id}/organizers/{player.id}",
        headers=headers,
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_remove_organizer_player_not_found(session: Session, client: TestClient):
    organizer = create_user_in_db(
        session, email="organizer@example.com", password="mypassword123"
    )
    tournament = create_tournament_in_db(session, organizer=organizer)
    headers = get_auth_headers(client, "organizer@example.com", "mypassword123")

    response = client.delete(
        f"/tournaments/{tournament.id}/organizers/00000000-0000-0000-0000-000000000000",
        headers=headers,
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_remove_organizer_player_has_no_user(session: Session, client: TestClient):
    """A guest player (no user account) cannot be removed as organizer."""
    organizer = create_user_in_db(
        session, email="organizer@example.com", password="mypassword123"
    )
    tournament = create_tournament_in_db(session, organizer=organizer)
    guest_player = create_player_in_db(
        session, guest_tournament=tournament, nickname="GuestPlayer"
    )
    headers = get_auth_headers(client, "organizer@example.com", "mypassword123")

    response = client.delete(
        f"/tournaments/{tournament.id}/organizers/{guest_player.id}",
        headers=headers,
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST


def test_remove_organizer_not_an_organizer(session: Session, client: TestClient):
    organizer = create_user_in_db(
        session, email="organizer@example.com", password="mypassword123"
    )
    tournament = create_tournament_in_db(session, organizer=organizer)
    headers = get_auth_headers(client, "organizer@example.com", "mypassword123")

    other_user = create_user_in_db(session, email="other@example.com")
    other_player = create_player_in_db(
        session, user=other_user, nickname="NotAnOrganizer"
    )

    response = client.delete(
        f"/tournaments/{tournament.id}/organizers/{other_player.id}",
        headers=headers,
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST


def test_remove_organizer_last_organizer(session: Session, client: TestClient):
    """Cannot remove the last organizer from a tournament."""
    organizer = create_user_in_db(
        session, email="organizer@example.com", password="mypassword123"
    )
    tournament = create_tournament_in_db(session, organizer=organizer)
    organizer_player = create_player_in_db(
        session, user=organizer, nickname="OnlyOrganizer"
    )
    headers = get_auth_headers(client, "organizer@example.com", "mypassword123")

    response = client.delete(
        f"/tournaments/{tournament.id}/organizers/{organizer_player.id}",
        headers=headers,
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST


def test_remove_organizer_unauthenticated(session: Session, client: TestClient):
    tournament = create_tournament_in_db(session)
    user = create_user_in_db(session, email="user@example.com")
    player = create_player_in_db(session, user=user, nickname="SomePlayer")

    response = client.delete(
        f"/tournaments/{tournament.id}/organizers/{player.id}",
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
