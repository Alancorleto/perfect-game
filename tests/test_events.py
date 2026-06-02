from unittest.mock import AsyncMock, patch

from fastapi import status
from fastapi.testclient import TestClient
from sqlmodel import Session

from models.round import RoundState
from tests.helpers import (
    add_organizer_to_event,
    create_event_in_db,
    create_player_in_db,
    create_round_in_db,
    create_tournament_in_db,
    create_user_in_db,
    get_auth_headers,
)

# ---------------------------------------------------------------------------
# GET /events/
# ---------------------------------------------------------------------------


def test_list_events(session: Session, client: TestClient):
    create_event_in_db(session, name="Event A", country_code="AR")
    create_event_in_db(session, name="Event B", country_code="BR")

    response = client.get("/events/")
    data = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert len(data) == 2
    names = [t["name"] for t in data]
    assert "Event A" in names
    assert "Event B" in names


def test_list_events_filtered_by_country(session: Session, client: TestClient):
    create_event_in_db(session, name="Event A", country_code="AR")
    create_event_in_db(session, name="Event B", country_code="BR")

    response = client.get("/events/?country_code=ar")
    data = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert len(data) == 1
    assert data[0]["name"] == "Event A"
    assert data[0]["country_code"] == "AR"


def test_list_events_filtered_by_country_with_no_matches(
    session: Session, client: TestClient
):
    create_event_in_db(session, name="Event A", country_code="AR")

    response = client.get("/events/?country_code=br")
    data = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert data == []


def test_list_events_empty(client: TestClient):
    response = client.get("/events/")

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == []


# ---------------------------------------------------------------------------
# GET /events/{event_id}
# ---------------------------------------------------------------------------


def test_get_event(session: Session, client: TestClient):
    event = create_event_in_db(session, name="My Event")

    response = client.get(f"/events/{event.id}")
    data = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert data["name"] == "My Event"
    assert data["id"] == str(event.id)


def test_get_event_not_found(client: TestClient):
    response = client.get("/events/00000000-0000-0000-0000-000000000000")

    assert response.status_code == status.HTTP_404_NOT_FOUND


# ---------------------------------------------------------------------------
# POST /events
# ---------------------------------------------------------------------------


def test_create_event(session: Session, client: TestClient):
    create_user_in_db(session, email="user@example.com", password="mypassword123")
    headers = get_auth_headers(client, "user@example.com", "mypassword123")

    response = client.post(
        "/events/",
        json={"name": "New Event", "country_code": "AR"},
        headers=headers,
    )
    data = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert data["name"] == "New Event"
    assert data["id"] is not None
    assert data["country_code"] == "AR"


def test_create_event_creator_becomes_organizer(session: Session, client: TestClient):
    create_user_in_db(session, email="user@example.com", password="mypassword123")
    headers = get_auth_headers(client, "user@example.com", "mypassword123")

    create_response = client.post(
        "/events/",
        json={"name": "New Event", "country_code": "AR"},
        headers=headers,
    )
    event_id = create_response.json()["id"]

    # The creator should be able to update the event (only organizers can)
    update_response = client.patch(
        f"/events/{event_id}",
        json={"name": "Updated Name"},
        headers=headers,
    )

    assert update_response.status_code == status.HTTP_200_OK


def test_create_event_unauthenticated(client: TestClient):
    response = client.post(
        "/events/",
        json={"name": "New Event", "country_code": "AR"},
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_create_event_with_long_name(session: Session, client: TestClient):
    """Test creating an event with an excessively long name."""
    create_user_in_db(session, email="organizer@example.com", password="mypassword123")
    headers = get_auth_headers(client, "organizer@example.com", "mypassword123")

    long_name = "T" * 300
    response = client.post(
        "/events/",
        json={"name": long_name, "country_code": "AR"},
        headers=headers,
    )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT


def test_create_event_with_empty_name(session: Session, client: TestClient):
    """Test creating an event with an empty name."""
    create_user_in_db(session, email="organizer@example.com", password="mypassword123")
    headers = get_auth_headers(client, "organizer@example.com", "mypassword123")

    response = client.post(
        "/events/",
        json={"name": "", "country_code": "AR"},
        headers=headers,
    )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT


# ---------------------------------------------------------------------------
# PATCH /events/{event_id}
# ---------------------------------------------------------------------------


def test_update_event(session: Session, client: TestClient):
    organizer = create_user_in_db(
        session, email="organizer@example.com", password="mypassword123"
    )
    event = create_event_in_db(session, organizer=organizer)
    headers = get_auth_headers(client, "organizer@example.com", "mypassword123")

    response = client.patch(
        f"/events/{event.id}",
        json={"name": "Updated Name"},
        headers=headers,
    )
    data = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert data["name"] == "Updated Name"


def test_update_event_not_found(session: Session, client: TestClient):
    create_user_in_db(session, email="user@example.com", password="mypassword123")
    headers = get_auth_headers(client, "user@example.com", "mypassword123")

    response = client.patch(
        "/events/00000000-0000-0000-0000-000000000000",
        json={"name": "Updated Name"},
        headers=headers,
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_update_event_unauthorized(session: Session, client: TestClient):
    create_user_in_db(session, email="attacker@example.com", password="mypassword123")
    event = create_event_in_db(session)
    headers = get_auth_headers(client, "attacker@example.com", "mypassword123")

    response = client.patch(
        f"/events/{event.id}",
        json={"name": "Hacked"},
        headers=headers,
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_update_event_as_super_admin(session: Session, client: TestClient):
    create_user_in_db(
        session,
        email="admin@example.com",
        password="mypassword123",
        is_super_admin=True,
    )
    event = create_event_in_db(session)
    headers = get_auth_headers(client, "admin@example.com", "mypassword123")

    response = client.patch(
        f"/events/{event.id}",
        json={"name": "Admin Updated"},
        headers=headers,
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["name"] == "Admin Updated"


def test_update_event_unauthenticated(session: Session, client: TestClient):
    event = create_event_in_db(session)

    response = client.patch(f"/events/{event.id}", json={"name": "Updated Name"})

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


# ---------------------------------------------------------------------------
# DELETE /events/{event_id}
# ---------------------------------------------------------------------------


def test_delete_event_empty(session: Session, client: TestClient):
    organizer = create_user_in_db(
        session, email="organizer@example.com", password="mypassword123"
    )
    event = create_event_in_db(session, organizer=organizer)
    headers = get_auth_headers(client, "organizer@example.com", "mypassword123")

    response = client.delete(f"/events/{event.id}", headers=headers)

    assert response.status_code == status.HTTP_204_NO_CONTENT

    get_response = client.get(f"/events/{event.id}", headers=headers)
    assert get_response.status_code == status.HTTP_404_NOT_FOUND


def test_delete_event_with_empty_tournament_and_round(
    session: Session, client: TestClient
):
    organizer = create_user_in_db(
        session, email="organizer@example.com", password="mypassword123"
    )
    event = create_event_in_db(session, organizer=organizer)
    tournament = create_tournament_in_db(session, event=event)
    create_round_in_db(session, tournament=tournament)

    headers = get_auth_headers(client, "organizer@example.com", "mypassword123")

    response = client.delete(f"/events/{event.id}", headers=headers)

    assert response.status_code == status.HTTP_204_NO_CONTENT

    get_response = client.get(f"/events/{event.id}", headers=headers)
    assert get_response.status_code == status.HTTP_404_NOT_FOUND


def test_delete_event_with_started_round(session: Session, client: TestClient):
    organizer = create_user_in_db(
        session, email="organizer@example.com", password="mypassword123"
    )
    event = create_event_in_db(session, organizer=organizer)
    tournament = create_tournament_in_db(session, event=event)
    create_round_in_db(session, tournament=tournament, state=RoundState.IN_PROGRESS)
    headers = get_auth_headers(client, "organizer@example.com", "mypassword123")

    response = client.delete(f"/events/{event.id}", headers=headers)
    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_delete_event_not_found(session: Session, client: TestClient):
    create_user_in_db(session, email="user@example.com", password="mypassword123")
    headers = get_auth_headers(client, "user@example.com", "mypassword123")

    response = client.delete(
        "/events/00000000-0000-0000-0000-000000000000", headers=headers
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_delete_event_unauthorized(session: Session, client: TestClient):
    create_user_in_db(session, email="attacker@example.com", password="mypassword123")
    event = create_event_in_db(session)
    headers = get_auth_headers(client, "attacker@example.com", "mypassword123")

    response = client.delete(f"/events/{event.id}", headers=headers)

    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_delete_event_as_super_admin(session: Session, client: TestClient):
    create_user_in_db(
        session,
        email="admin@example.com",
        password="mypassword123",
        is_super_admin=True,
    )
    event = create_event_in_db(session)
    headers = get_auth_headers(client, "admin@example.com", "mypassword123")

    response = client.delete(f"/events/{event.id}", headers=headers)

    assert response.status_code == status.HTTP_204_NO_CONTENT


def test_delete_event_unauthenticated(session: Session, client: TestClient):
    event = create_event_in_db(session)

    response = client.delete(f"/events/{event.id}")

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


# ---------------------------------------------------------------------------
# GET /events/{event_id}/tournaments
# ---------------------------------------------------------------------------


def test_list_event_tournaments_empty(session: Session, client: TestClient):
    event = create_event_in_db(session)

    response = client.get(f"/events/{event.id}/tournaments")

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == []


def test_list_event_tournaments_not_found(client: TestClient):
    response = client.get("/events/00000000-0000-0000-0000-000000000000/tournaments")

    assert response.status_code == status.HTTP_404_NOT_FOUND


# ---------------------------------------------------------------------------
# GET /events/{event_id}/organizers
# ---------------------------------------------------------------------------


def test_list_event_organizers(session: Session, client: TestClient):
    organizer = create_user_in_db(session, email="organizer@example.com")
    create_player_in_db(session, user=organizer, nickname="OrganizerPlayer")
    event = create_event_in_db(session, organizer=organizer)

    response = client.get(f"/events/{event.id}/organizers")
    data = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert len(data) == 1
    assert data[0]["nickname"] == "OrganizerPlayer"


def test_list_event_organizers_without_player_profile(
    session: Session, client: TestClient
):
    """Organizers without a player profile are excluded from the response."""
    organizer = create_user_in_db(session, email="organizer@example.com")
    event = create_event_in_db(session, organizer=organizer)

    response = client.get(f"/events/{event.id}/organizers")

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == []


def test_list_event_organizers_not_found(client: TestClient):
    response = client.get("/events/00000000-0000-0000-0000-000000000000/organizers")

    assert response.status_code == status.HTTP_404_NOT_FOUND


# ---------------------------------------------------------------------------
# POST /events/{event_id}/organizers/{player_id}
# ---------------------------------------------------------------------------


def test_add_organizer(session: Session, client: TestClient):
    organizer = create_user_in_db(
        session, email="organizer@example.com", password="mypassword123"
    )
    event = create_event_in_db(session, organizer=organizer)
    headers = get_auth_headers(client, "organizer@example.com", "mypassword123")

    new_user = create_user_in_db(session, email="new@example.com")
    new_player = create_player_in_db(session, user=new_user, nickname="NewOrganizer")

    response = client.post(
        f"/events/{event.id}/organizers/{new_player.id}",
        headers=headers,
    )
    data = response.json()

    assert response.status_code == status.HTTP_200_OK
    nicknames = [p["nickname"] for p in data]
    assert "NewOrganizer" in nicknames


def test_add_organizer_event_not_found(session: Session, client: TestClient):
    organizer = create_user_in_db(
        session, email="organizer@example.com", password="mypassword123"
    )
    player = create_player_in_db(session, user=organizer, nickname="SomePlayer")
    headers = get_auth_headers(client, "organizer@example.com", "mypassword123")

    response = client.post(
        f"/events/00000000-0000-0000-0000-000000000000/organizers/{player.id}",
        headers=headers,
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_add_organizer_unauthorized(session: Session, client: TestClient):
    create_user_in_db(session, email="attacker@example.com", password="mypassword123")
    event = create_event_in_db(session)
    new_user = create_user_in_db(session, email="new@example.com")
    new_player = create_player_in_db(session, user=new_user, nickname="NewOrganizer")
    headers = get_auth_headers(client, "attacker@example.com", "mypassword123")

    response = client.post(
        f"/events/{event.id}/organizers/{new_player.id}",
        headers=headers,
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_add_organizer_player_not_found(session: Session, client: TestClient):
    organizer = create_user_in_db(
        session, email="organizer@example.com", password="mypassword123"
    )
    event = create_event_in_db(session, organizer=organizer)
    headers = get_auth_headers(client, "organizer@example.com", "mypassword123")

    response = client.post(
        f"/events/{event.id}/organizers/00000000-0000-0000-0000-000000000000",
        headers=headers,
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_add_organizer_player_has_no_user(session: Session, client: TestClient):
    """A guest player (no user account) cannot be added as organizer."""
    organizer = create_user_in_db(
        session, email="organizer@example.com", password="mypassword123"
    )
    event = create_event_in_db(session, organizer=organizer)
    guest_player = create_player_in_db(
        session, guest_event=event, nickname="GuestPlayer"
    )
    headers = get_auth_headers(client, "organizer@example.com", "mypassword123")

    response = client.post(
        f"/events/{event.id}/organizers/{guest_player.id}",
        headers=headers,
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST


def test_add_organizer_already_organizer(session: Session, client: TestClient):
    organizer = create_user_in_db(
        session, email="organizer@example.com", password="mypassword123"
    )
    event = create_event_in_db(session, organizer=organizer)
    organizer_player = create_player_in_db(
        session, user=organizer, nickname="OrganizerPlayer"
    )
    headers = get_auth_headers(client, "organizer@example.com", "mypassword123")

    response = client.post(
        f"/events/{event.id}/organizers/{organizer_player.id}",
        headers=headers,
    )

    assert response.status_code == status.HTTP_409_CONFLICT


def test_add_organizer_unauthenticated(session: Session, client: TestClient):
    event = create_event_in_db(session)
    user = create_user_in_db(session, email="user@example.com")
    player = create_player_in_db(session, user=user, nickname="SomePlayer")

    response = client.post(
        f"/events/{event.id}/organizers/{player.id}",
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


# ---------------------------------------------------------------------------
# DELETE /events/{event_id}/organizers/{player_id}
# ---------------------------------------------------------------------------


def test_remove_organizer(session: Session, client: TestClient):
    organizer = create_user_in_db(
        session, email="organizer@example.com", password="mypassword123"
    )
    event = create_event_in_db(session, organizer=organizer)
    headers = get_auth_headers(client, "organizer@example.com", "mypassword123")

    # Add a second organizer (needed so the first can be removed)
    second_user = create_user_in_db(session, email="second@example.com")
    second_player = create_player_in_db(
        session, user=second_user, nickname="SecondOrganizer"
    )
    add_organizer_to_event(session, event, second_user)

    response = client.delete(
        f"/events/{event.id}/organizers/{second_player.id}",
        headers=headers,
    )
    data = response.json()

    assert response.status_code == status.HTTP_200_OK
    nicknames = [p["nickname"] for p in data]
    assert "SecondOrganizer" not in nicknames


def test_remove_organizer_event_not_found(session: Session, client: TestClient):
    organizer = create_user_in_db(
        session, email="organizer@example.com", password="mypassword123"
    )
    player = create_player_in_db(session, user=organizer, nickname="SomePlayer")
    headers = get_auth_headers(client, "organizer@example.com", "mypassword123")

    response = client.delete(
        f"/events/00000000-0000-0000-0000-000000000000/organizers/{player.id}",
        headers=headers,
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_remove_organizer_unauthorized(session: Session, client: TestClient):
    create_user_in_db(session, email="attacker@example.com", password="mypassword123")
    event = create_event_in_db(session)
    user = create_user_in_db(session, email="user@example.com")
    player = create_player_in_db(session, user=user, nickname="SomePlayer")
    headers = get_auth_headers(client, "attacker@example.com", "mypassword123")

    response = client.delete(
        f"/events/{event.id}/organizers/{player.id}",
        headers=headers,
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_remove_organizer_player_not_found(session: Session, client: TestClient):
    organizer = create_user_in_db(
        session, email="organizer@example.com", password="mypassword123"
    )
    event = create_event_in_db(session, organizer=organizer)
    headers = get_auth_headers(client, "organizer@example.com", "mypassword123")

    response = client.delete(
        f"/events/{event.id}/organizers/00000000-0000-0000-0000-000000000000",
        headers=headers,
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_remove_organizer_player_has_no_user(session: Session, client: TestClient):
    """A guest player (no user account) cannot be removed as organizer."""
    organizer = create_user_in_db(
        session, email="organizer@example.com", password="mypassword123"
    )
    event = create_event_in_db(session, organizer=organizer)
    guest_player = create_player_in_db(
        session, guest_event=event, nickname="GuestPlayer"
    )
    headers = get_auth_headers(client, "organizer@example.com", "mypassword123")

    response = client.delete(
        f"/events/{event.id}/organizers/{guest_player.id}",
        headers=headers,
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST


def test_remove_organizer_not_an_organizer(session: Session, client: TestClient):
    organizer = create_user_in_db(
        session, email="organizer@example.com", password="mypassword123"
    )
    event = create_event_in_db(session, organizer=organizer)
    headers = get_auth_headers(client, "organizer@example.com", "mypassword123")

    other_user = create_user_in_db(session, email="other@example.com")
    other_player = create_player_in_db(
        session, user=other_user, nickname="NotAnOrganizer"
    )

    response = client.delete(
        f"/events/{event.id}/organizers/{other_player.id}",
        headers=headers,
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST


def test_remove_organizer_last_organizer(session: Session, client: TestClient):
    """Cannot remove the last organizer from an event."""
    organizer = create_user_in_db(
        session, email="organizer@example.com", password="mypassword123"
    )
    event = create_event_in_db(session, organizer=organizer)
    organizer_player = create_player_in_db(
        session, user=organizer, nickname="OnlyOrganizer"
    )
    headers = get_auth_headers(client, "organizer@example.com", "mypassword123")

    response = client.delete(
        f"/events/{event.id}/organizers/{organizer_player.id}",
        headers=headers,
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST


def test_remove_organizer_unauthenticated(session: Session, client: TestClient):
    event = create_event_in_db(session)
    user = create_user_in_db(session, email="user@example.com")
    player = create_player_in_db(session, user=user, nickname="SomePlayer")

    response = client.delete(
        f"/events/{event.id}/organizers/{player.id}",
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


# ---------------------------------------------------------------------------
# POST /events/{event_id}/logo
# ---------------------------------------------------------------------------


def test_upload_event_logo(session: Session, client: TestClient):
    organizer = create_user_in_db(
        session, email="organizer@example.com", password="mypassword123"
    )
    event = create_event_in_db(session, organizer=organizer)
    headers = get_auth_headers(client, "organizer@example.com", "mypassword123")

    expected_url = "https://example.com/event-logo.png"

    with patch(
        "routers.events.upload_image",
        new=AsyncMock(return_value=expected_url),
    ) as mock_upload_image:
        response = client.post(
            f"/events/{event.id}/logo",
            files={"logo": ("logo.png", b"fake image bytes", "image/png")},
            headers=headers,
        )

    data = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert data["logo_url"] == expected_url
    assert data["id"] == str(event.id)
    mock_upload_image.assert_awaited_once_with(
        b"fake image bytes",
        f"{event.id}.png",
        "event_logos",
    )


def test_upload_event_logo_not_found(session: Session, client: TestClient):
    create_user_in_db(session, email="organizer@example.com", password="mypassword123")
    headers = get_auth_headers(client, "organizer@example.com", "mypassword123")

    response = client.post(
        "/events/00000000-0000-0000-0000-000000000000/logo",
        files={"logo": ("logo.png", b"fake image bytes", "image/png")},
        headers=headers,
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_upload_event_logo_unauthorized(session: Session, client: TestClient):
    create_user_in_db(session, email="attacker@example.com", password="mypassword123")
    event = create_event_in_db(session)
    headers = get_auth_headers(client, "attacker@example.com", "mypassword123")

    response = client.post(
        f"/events/{event.id}/logo",
        files={"logo": ("logo.png", b"fake image bytes", "image/png")},
        headers=headers,
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_upload_event_logo_unauthenticated(session: Session, client: TestClient):
    event = create_event_in_db(session)

    response = client.post(
        f"/events/{event.id}/logo",
        files={"logo": ("logo.png", b"fake image bytes", "image/png")},
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
