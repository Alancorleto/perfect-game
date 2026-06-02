from fastapi import status
from fastapi.testclient import TestClient
from sqlmodel import Session

from models.category_invitation import (
    CategoryInvitation,
    CategoryJoinRequest,
    RequestStatus,
)
from models.round import RoundState
from tests.helpers import (
    create_category_in_db,
    create_event_in_db,
    create_player_in_db,
    create_round_in_db,
    create_user_in_db,
    get_auth_headers,
)

# ---------------------------------------------------------------------------
# GET /categories/
# ---------------------------------------------------------------------------


def test_list_categories(session: Session, client: TestClient):
    event = create_event_in_db(session)
    create_category_in_db(session, event=event, name="Category A")
    create_category_in_db(session, event=event, name="Category B")

    response = client.get("/categories/")
    data = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert len(data) == 2
    names = [c["name"] for c in data]
    assert "Category A" in names
    assert "Category B" in names


def test_list_categories_empty(client: TestClient):
    response = client.get("/categories/")

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == []


# ---------------------------------------------------------------------------
# GET /categories/{category_id}
# ---------------------------------------------------------------------------


def test_get_category(session: Session, client: TestClient):
    event = create_event_in_db(session)
    category = create_category_in_db(session, event=event, name="My Category")

    response = client.get(f"/categories/{category.id}")
    data = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert data["id"] == str(category.id)
    assert data["name"] == "My Category"
    assert data["event_id"] == str(event.id)


def test_get_category_not_found(client: TestClient):
    response = client.get("/categories/00000000-0000-0000-0000-000000000000")

    assert response.status_code == status.HTTP_404_NOT_FOUND


# ---------------------------------------------------------------------------
# POST /categories/
# ---------------------------------------------------------------------------


def test_create_category(session: Session, client: TestClient):
    organizer = create_user_in_db(
        session, email="organizer@example.com", password="mypassword123"
    )
    event = create_event_in_db(session, organizer=organizer)
    headers = get_auth_headers(client, "organizer@example.com", "mypassword123")

    response = client.post(
        "/categories/",
        json={"name": "New Category", "event_id": str(event.id)},
        headers=headers,
    )
    data = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert data["id"] is not None
    assert data["name"] == "New Category"
    assert data["event_id"] == str(event.id)


def test_create_category_event_not_found(session: Session, client: TestClient):
    create_user_in_db(session, email="user@example.com", password="mypassword123")
    headers = get_auth_headers(client, "user@example.com", "mypassword123")

    response = client.post(
        "/categories/",
        json={
            "name": "New Category",
            "event_id": "00000000-0000-0000-0000-000000000000",
        },
        headers=headers,
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_create_category_unauthorized(session: Session, client: TestClient):
    create_user_in_db(session, email="attacker@example.com", password="mypassword123")
    event = create_event_in_db(session)
    headers = get_auth_headers(client, "attacker@example.com", "mypassword123")

    response = client.post(
        "/categories/",
        json={"name": "New Category", "event_id": str(event.id)},
        headers=headers,
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_create_category_as_super_admin(session: Session, client: TestClient):
    create_user_in_db(
        session,
        email="admin@example.com",
        password="mypassword123",
        is_super_admin=True,
    )
    event = create_event_in_db(session)
    headers = get_auth_headers(client, "admin@example.com", "mypassword123")

    response = client.post(
        "/categories/",
        json={"name": "Admin Category", "event_id": str(event.id)},
        headers=headers,
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["name"] == "Admin Category"


def test_create_category_unauthenticated(session: Session, client: TestClient):
    event = create_event_in_db(session)

    response = client.post(
        "/categories/",
        json={"name": "New Category", "event_id": str(event.id)},
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_create_category_missing_name(session: Session, client: TestClient):
    organizer = create_user_in_db(
        session, email="organizer@example.com", password="mypassword123"
    )
    event = create_event_in_db(session, organizer=organizer)
    headers = get_auth_headers(client, "organizer@example.com", "mypassword123")

    response = client.post(
        "/categories/",
        json={"event_id": str(event.id)},
        headers=headers,
    )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT


# ---------------------------------------------------------------------------
# PATCH /categories/{category_id}
# ---------------------------------------------------------------------------


def test_update_category(session: Session, client: TestClient):
    organizer = create_user_in_db(
        session, email="organizer@example.com", password="mypassword123"
    )
    event = create_event_in_db(session, organizer=organizer)
    category = create_category_in_db(session, event=event, name="Old Name")
    headers = get_auth_headers(client, "organizer@example.com", "mypassword123")

    response = client.patch(
        f"/categories/{category.id}",
        json={"name": "Updated Name"},
        headers=headers,
    )
    data = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert data["name"] == "Updated Name"
    assert data["event_id"] == str(event.id)


def test_update_category_not_found(session: Session, client: TestClient):
    create_user_in_db(session, email="user@example.com", password="mypassword123")
    headers = get_auth_headers(client, "user@example.com", "mypassword123")

    response = client.patch(
        "/categories/00000000-0000-0000-0000-000000000000",
        json={"name": "Updated Name"},
        headers=headers,
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_update_category_unauthorized(session: Session, client: TestClient):
    create_user_in_db(session, email="attacker@example.com", password="mypassword123")
    event = create_event_in_db(session)
    category = create_category_in_db(session, event=event)
    headers = get_auth_headers(client, "attacker@example.com", "mypassword123")

    response = client.patch(
        f"/categories/{category.id}",
        json={"name": "Hacked"},
        headers=headers,
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_update_category_as_super_admin(session: Session, client: TestClient):
    create_user_in_db(
        session,
        email="admin@example.com",
        password="mypassword123",
        is_super_admin=True,
    )
    event = create_event_in_db(session)
    category = create_category_in_db(session, event=event)
    headers = get_auth_headers(client, "admin@example.com", "mypassword123")

    response = client.patch(
        f"/categories/{category.id}",
        json={"name": "Admin Updated"},
        headers=headers,
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["name"] == "Admin Updated"


def test_update_category_unauthenticated(session: Session, client: TestClient):
    event = create_event_in_db(session)
    category = create_category_in_db(session, event=event)

    response = client.patch(f"/categories/{category.id}", json={"name": "Updated"})

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


# ---------------------------------------------------------------------------
# DELETE /categories/{category_id}
# ---------------------------------------------------------------------------


def test_delete_category_empty(session: Session, client: TestClient):
    organizer = create_user_in_db(
        session, email="organizer@example.com", password="mypassword123"
    )
    event = create_event_in_db(session, organizer=organizer)
    category = create_category_in_db(session, event=event)
    headers = get_auth_headers(client, "organizer@example.com", "mypassword123")

    response = client.delete(f"/categories/{category.id}", headers=headers)

    assert response.status_code == status.HTTP_204_NO_CONTENT

    get_response = client.get(f"/categories/{category.id}", headers=headers)
    assert get_response.status_code == status.HTTP_404_NOT_FOUND


def test_delete_category_with_a_started_round(session: Session, client: TestClient):
    create_user_in_db(session, email="organizer@example.com", password="mypassword123")
    headers = get_auth_headers(client, "organizer@example.com", "mypassword123")

    event = create_event_in_db(session)
    category = create_category_in_db(session, event=event)
    create_round_in_db(session, category=category, state=RoundState.IN_PROGRESS)

    response = client.delete(f"/categories/{category.id}", headers=headers)

    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_delete_category_not_found(session: Session, client: TestClient):
    create_user_in_db(session, email="user@example.com", password="mypassword123")
    headers = get_auth_headers(client, "user@example.com", "mypassword123")

    response = client.delete(
        "/categories/00000000-0000-0000-0000-000000000000",
        headers=headers,
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_delete_category_unauthorized(session: Session, client: TestClient):
    create_user_in_db(session, email="attacker@example.com", password="mypassword123")
    event = create_event_in_db(session)
    category = create_category_in_db(session, event=event)
    headers = get_auth_headers(client, "attacker@example.com", "mypassword123")

    response = client.delete(f"/categories/{category.id}", headers=headers)

    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_delete_category_as_super_admin(session: Session, client: TestClient):
    create_user_in_db(
        session,
        email="admin@example.com",
        password="mypassword123",
        is_super_admin=True,
    )
    event = create_event_in_db(session)
    category = create_category_in_db(session, event=event)
    headers = get_auth_headers(client, "admin@example.com", "mypassword123")

    response = client.delete(f"/categories/{category.id}", headers=headers)

    assert response.status_code == status.HTTP_204_NO_CONTENT


def test_delete_category_unauthenticated(session: Session, client: TestClient):
    event = create_event_in_db(session)
    category = create_category_in_db(session, event=event)

    response = client.delete(f"/categories/{category.id}")

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_delete_event_cascade(session: Session, client: TestClient):
    organizer = create_user_in_db(
        session,
        email="organizer@example.com",
        password="mypassword123",
        is_super_admin=True,
    )
    headers = get_auth_headers(client, "organizer@example.com", "mypassword123")
    event = create_event_in_db(session, organizer=organizer)
    category = create_category_in_db(session, event=event)

    response = client.delete(f"/events/{event.id}", headers=headers)

    assert response.status_code == status.HTTP_204_NO_CONTENT

    response = client.get(f"/categories/{category.id}")
    assert response.status_code == status.HTTP_404_NOT_FOUND


# ---------------------------------------------------------------------------
# POST /categories/{category_id}/players/bulk
# ---------------------------------------------------------------------------


def test_bulk_add_players_to_category(session: Session, client: TestClient):
    organizer = create_user_in_db(
        session, email="organizer@example.com", password="mypassword123"
    )
    event = create_event_in_db(session, organizer=organizer)
    category = create_category_in_db(session, event=event)
    player_a = create_player_in_db(session, nickname="PlayerA")
    player_b = create_player_in_db(session, nickname="PlayerB")
    headers = get_auth_headers(client, "organizer@example.com", "mypassword123")

    response = client.post(
        f"/categories/{category.id}/players/bulk",
        json=[str(player_a.id), str(player_b.id)],
        headers=headers,
    )
    data = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert len(data) == 2
    nicknames = [p["nickname"] for p in data]
    assert "PlayerA" in nicknames
    assert "PlayerB" in nicknames


def test_bulk_add_players_category_not_found(session: Session, client: TestClient):
    create_user_in_db(session, email="user@example.com", password="mypassword123")
    player = create_player_in_db(session, nickname="PlayerA")
    headers = get_auth_headers(client, "user@example.com", "mypassword123")

    response = client.post(
        "/categories/00000000-0000-0000-0000-000000000000/players/bulk",
        json=[str(player.id)],
        headers=headers,
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_bulk_add_players_unauthorized(session: Session, client: TestClient):
    create_user_in_db(session, email="attacker@example.com", password="mypassword123")
    event = create_event_in_db(session)
    category = create_category_in_db(session, event=event)
    player = create_player_in_db(session, nickname="PlayerA")
    headers = get_auth_headers(client, "attacker@example.com", "mypassword123")

    response = client.post(
        f"/categories/{category.id}/players/bulk",
        json=[str(player.id)],
        headers=headers,
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_bulk_add_players_player_not_found(session: Session, client: TestClient):
    organizer = create_user_in_db(
        session, email="organizer@example.com", password="mypassword123"
    )
    event = create_event_in_db(session, organizer=organizer)
    category = create_category_in_db(session, event=event)
    headers = get_auth_headers(client, "organizer@example.com", "mypassword123")

    response = client.post(
        f"/categories/{category.id}/players/bulk",
        json=["00000000-0000-0000-0000-000000000000"],
        headers=headers,
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_bulk_add_players_unauthenticated(session: Session, client: TestClient):
    event = create_event_in_db(session)
    category = create_category_in_db(session, event=event)
    player = create_player_in_db(session, nickname="PlayerA")

    response = client.post(
        f"/categories/{category.id}/players/bulk",
        json=[str(player.id)],
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


# ---------------------------------------------------------------------------
# POST /categories/{category_id}/invitations/{player_id}/
# ---------------------------------------------------------------------------


def test_invite_player_to_category(session: Session, client: TestClient):
    """Test inviting a player to a category"""
    organizer_user = create_user_in_db(
        session, email="organizer@example.com", password="mypassword123"
    )
    event = create_event_in_db(session, organizer=organizer_user)
    category = create_category_in_db(session, event=event)

    player_user = create_user_in_db(
        session, email="player@example.com", password="mypassword123"
    )
    player = create_player_in_db(session, nickname="PlayerA", user=player_user)

    headers = get_auth_headers(client, "organizer@example.com", "mypassword123")

    response = client.post(
        f"/categories/{category.id}/invitations/{player.id}/",
        headers=headers,
    )

    assert response.status_code == status.HTTP_204_NO_CONTENT

    session.refresh(category)
    assert len(category.invitations) == 1
    assert category.invitations[0].player_id == player.id


def test_invite_player_to_category_organizer(session: Session, client: TestClient):
    """Test inviting an organizer to their own category"""
    user = create_user_in_db(
        session, email="user@example.com", password="mypassword123"
    )
    event = create_event_in_db(session, organizer=user)
    category = create_category_in_db(session, event=event)
    player = create_player_in_db(session, user=user)

    response = client.post(
        f"/categories/{category.id}/invitations/{player.id}/",
        headers=get_auth_headers(client, "user@example.com", "mypassword123"),
    )

    assert response.status_code == status.HTTP_204_NO_CONTENT

    session.refresh(category)
    assert len(category.get_players_by_nickname()) == 1
    assert category.get_players_by_nickname()[0].id == player.id


def test_invite_player_to_category_category_not_found(
    session: Session, client: TestClient
):
    """Test inviting a player to a non-existent category"""
    user = create_user_in_db(
        session, email="user@example.com", password="mypassword123"
    )
    player = create_player_in_db(session, user=user)

    response = client.post(
        f"/categories/00000000-0000-0000-0000-000000000000/invitations/{player.id}/",
        headers=get_auth_headers(client, "user@example.com", "mypassword123"),
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_invite_player_to_category_player_not_found(
    session: Session, client: TestClient
):
    """Test inviting a non-existent player to a category"""
    user = create_user_in_db(
        session, email="user@example.com", password="mypassword123"
    )
    event = create_event_in_db(session, organizer=user)
    category = create_category_in_db(session, event=event)

    response = client.post(
        f"/categories/{category.id}/invitations/00000000-0000-0000-0000-000000000000/",
        headers=get_auth_headers(client, "user@example.com", "mypassword123"),
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_invite_player_to_category_player_not_registered(
    session: Session, client: TestClient
):
    """Test inviting a player without a user to a category"""
    user = create_user_in_db(
        session, email="user@example.com", password="mypassword123"
    )
    event = create_event_in_db(session, organizer=user)
    category = create_category_in_db(session, event=event)
    player = create_player_in_db(session, user=None)

    response = client.post(
        f"/categories/{category.id}/invitations/{player.id}/",
        headers=get_auth_headers(client, "user@example.com", "mypassword123"),
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST


def test_invite_player_to_category_player_already_in_category(
    session: Session, client: TestClient
):
    """Test inviting a player who is already in the category"""
    organizer = create_user_in_db(
        session, email="organizer@example.com", password="mypassword123"
    )
    player_user = create_user_in_db(
        session, email="player@example.com", password="mypassword123"
    )
    player = create_player_in_db(session, user=player_user)
    event = create_event_in_db(session, organizer=organizer)
    category = create_category_in_db(session, event=event)
    category.add_player(player)
    session.commit()

    response = client.post(
        f"/categories/{category.id}/invitations/{player.id}/",
        headers=get_auth_headers(client, "organizer@example.com", "mypassword123"),
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST


def test_invite_player_to_category_invitation_declined(
    session: Session, client: TestClient
):
    """Test inviting a player who has declined the invitation"""
    organizer = create_user_in_db(
        session, email="organizer@example.com", password="mypassword123"
    )
    player_user = create_user_in_db(
        session, email="player@example.com", password="mypassword123"
    )
    player = create_player_in_db(session, user=player_user)
    event = create_event_in_db(session, organizer=organizer)
    category = create_category_in_db(session, event=event)
    invitation = CategoryInvitation(
        player_id=player.id,
        category_id=category.id,
        status=RequestStatus.DECLINED,
    )
    session.add(invitation)
    session.commit()

    response = client.post(
        f"/categories/{category.id}/invitations/{player.id}/",
        headers=get_auth_headers(client, "organizer@example.com", "mypassword123"),
    )

    assert response.status_code == status.HTTP_204_NO_CONTENT

    session.refresh(invitation)
    assert invitation.status == RequestStatus.PENDING


# ---------------------------------------------------------------------------
# POST /categories/{category_id}/invitations/accept
# ---------------------------------------------------------------------------


def test_accept_category_invitation(session: Session, client: TestClient):
    """Test accepting a category invitation"""
    user = create_user_in_db(
        session, email="user@example.com", password="mypassword123"
    )
    player = create_player_in_db(session, user=user)
    event = create_event_in_db(session, organizer=user)
    category = create_category_in_db(session, event=event)
    invitation = CategoryInvitation(category_id=category.id, player_id=player.id)
    session.add(invitation)
    session.commit()

    response = client.post(
        f"/categories/{category.id}/invitations/accept",
        headers=get_auth_headers(client, "user@example.com", "mypassword123"),
    )

    assert response.status_code == status.HTTP_200_OK

    session.refresh(category)
    assert len(category.get_players_by_nickname()) == 1
    assert category.get_players_by_nickname()[0].id == player.id


def test_accept_category_invitation_no_player(session: Session, client: TestClient):
    """Test accepting an invitation without an associated player"""
    user = create_user_in_db(
        session, email="user@example.com", password="mypassword123"
    )
    event = create_event_in_db(session, organizer=user)
    category = create_category_in_db(session, event=event)

    response = client.post(
        f"/categories/{category.id}/invitations/accept",
        headers=get_auth_headers(client, "user@example.com", "mypassword123"),
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST


def test_accept_category_invitation_category_not_found(
    session: Session, client: TestClient
):
    """Test accepting an invitation for a non-existent category"""
    user = create_user_in_db(
        session, email="user@example.com", password="mypassword123"
    )
    create_player_in_db(session, user=user)

    response = client.post(
        "/categories/00000000-0000-0000-0000-000000000000/invitations/accept",
        headers=get_auth_headers(client, "user@example.com", "mypassword123"),
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_accept_category_invitation_not_found(session: Session, client: TestClient):
    """Test accepting a non-existent invitation"""
    user = create_user_in_db(
        session, email="user@example.com", password="mypassword123"
    )
    create_player_in_db(session, user=user)
    event = create_event_in_db(session, organizer=user)
    category = create_category_in_db(session, event=event)

    response = client.post(
        f"/categories/{category.id}/invitations/accept",
        headers=get_auth_headers(client, "user@example.com", "mypassword123"),
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_accept_category_invitation_already_accepted(
    session: Session, client: TestClient
):
    """Test accepting an already accepted invitation"""
    user = create_user_in_db(
        session, email="user@example.com", password="mypassword123"
    )
    player = create_player_in_db(session, user=user)
    event = create_event_in_db(session, organizer=user)
    category = create_category_in_db(session, event=event)
    invitation = CategoryInvitation(
        category_id=category.id, player_id=player.id, status=RequestStatus.ACCEPTED
    )
    session.add(invitation)
    session.commit()

    response = client.post(
        f"/categories/{category.id}/invitations/accept",
        headers=get_auth_headers(client, "user@example.com", "mypassword123"),
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST


# ---------------------------------------------------------------------------
# POST /categories/{category_id}/invitations/decline
# ---------------------------------------------------------------------------


def test_decline_category_invitation(session: Session, client: TestClient):
    """Test declining a category invitation"""
    user = create_user_in_db(
        session, email="user@example.com", password="mypassword123"
    )
    player = create_player_in_db(session, user=user)
    event = create_event_in_db(session, organizer=user)
    category = create_category_in_db(session, event=event)
    invitation = CategoryInvitation(category_id=category.id, player_id=player.id)
    session.add(invitation)
    session.commit()

    response = client.post(
        f"/categories/{category.id}/invitations/decline",
        headers=get_auth_headers(client, "user@example.com", "mypassword123"),
    )

    assert response.status_code == status.HTTP_200_OK

    session.refresh(invitation)
    assert invitation.status == RequestStatus.DECLINED
    session.refresh(category)
    assert len(category.get_players_by_nickname()) == 0


def test_decline_category_invitation_no_player(session: Session, client: TestClient):
    """Test declining an invitation without an associated player"""
    user = create_user_in_db(
        session, email="user@example.com", password="mypassword123"
    )
    event = create_event_in_db(session, organizer=user)
    category = create_category_in_db(session, event=event)

    response = client.post(
        f"/categories/{category.id}/invitations/decline",
        headers=get_auth_headers(client, "user@example.com", "mypassword123"),
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST


def test_decline_category_invitation_category_not_found(
    session: Session, client: TestClient
):
    """Test declining an invitation for a non-existent category"""
    user = create_user_in_db(
        session, email="user@example.com", password="mypassword123"
    )
    create_player_in_db(session, user=user)

    response = client.post(
        "/categories/00000000-0000-0000-0000-000000000000/invitations/decline",
        headers=get_auth_headers(client, "user@example.com", "mypassword123"),
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_decline_category_invitation_not_found(session: Session, client: TestClient):
    """Test declining a non-existent invitation"""
    user = create_user_in_db(
        session, email="user@example.com", password="mypassword123"
    )
    create_player_in_db(session, user=user)
    event = create_event_in_db(session, organizer=user)
    category = create_category_in_db(session, event=event)

    response = client.post(
        f"/categories/{category.id}/invitations/decline",
        headers=get_auth_headers(client, "user@example.com", "mypassword123"),
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_decline_category_invitation_already_declined(
    session: Session, client: TestClient
):
    """Test declining an already declined invitation"""
    user = create_user_in_db(
        session, email="user@example.com", password="mypassword123"
    )
    player = create_player_in_db(session, user=user)
    event = create_event_in_db(session, organizer=user)
    category = create_category_in_db(session, event=event)
    invitation = CategoryInvitation(
        category_id=category.id, player_id=player.id, status=RequestStatus.DECLINED
    )
    session.add(invitation)
    session.commit()

    response = client.post(
        f"/categories/{category.id}/invitations/decline",
        headers=get_auth_headers(client, "user@example.com", "mypassword123"),
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST


def test_decline_category_invitation_already_accepted(
    session: Session, client: TestClient
):
    """Test declining an already accepted invitation"""
    user = create_user_in_db(
        session, email="user@example.com", password="mypassword123"
    )
    player = create_player_in_db(session, user=user)
    event = create_event_in_db(session, organizer=user)
    category = create_category_in_db(session, event=event)
    invitation = CategoryInvitation(
        category_id=category.id, player_id=player.id, status=RequestStatus.ACCEPTED
    )
    session.add(invitation)
    session.commit()

    response = client.post(
        f"/categories/{category.id}/invitations/decline",
        headers=get_auth_headers(client, "user@example.com", "mypassword123"),
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST


# ---------------------------------------------------------------------------
# GET /categories/{category_id}/invitations
# ---------------------------------------------------------------------------


def test_list_category_invitations(session: Session, client: TestClient):
    """Test listing category invitations"""
    organizer = create_user_in_db(
        session, email="organizer@example.com", password="mypassword123"
    )
    invited_user = create_user_in_db(
        session, email="invited@example.com", password="mypassword123"
    )
    invited_player = create_player_in_db(session, user=invited_user)
    event = create_event_in_db(session, organizer=organizer)
    category = create_category_in_db(session, event=event)
    invitation = CategoryInvitation(
        category_id=category.id,
        player_id=invited_player.id,
        status=RequestStatus.PENDING,
    )
    session.add(invitation)
    session.commit()

    response = client.get(
        f"/categories/{category.id}/invitations",
        headers=get_auth_headers(client, "organizer@example.com", "mypassword123"),
    )
    data = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert len(data) == 1
    assert data[0]["status"] == RequestStatus.PENDING.value
    assert data[0]["category_id"] == str(category.id)
    assert data[0]["player"]["id"] == str(invited_player.id)


def test_list_category_invitations_empty(session: Session, client: TestClient):
    """Test listing invitations for a category without invitations"""
    organizer = create_user_in_db(
        session, email="organizer@example.com", password="mypassword123"
    )
    event = create_event_in_db(session, organizer=organizer)
    category = create_category_in_db(session, event=event)

    response = client.get(
        f"/categories/{category.id}/invitations",
        headers=get_auth_headers(client, "organizer@example.com", "mypassword123"),
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == []


def test_list_category_invitations_not_found(session: Session, client: TestClient):
    """Test listing invitations for a non-existent category"""
    create_user_in_db(session, email="organizer@example.com", password="mypassword123")

    response = client.get(
        "/categories/00000000-0000-0000-0000-000000000000/invitations",
        headers=get_auth_headers(client, "organizer@example.com", "mypassword123"),
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_list_category_invitations_unauthorized(session: Session, client: TestClient):
    """Test listing invitations without permission"""
    organizer = create_user_in_db(
        session, email="organizer@example.com", password="mypassword123"
    )
    create_user_in_db(session, email="attacker@example.com", password="mypassword123")
    event = create_event_in_db(session, organizer=organizer)
    category = create_category_in_db(session, event=event)

    response = client.get(
        f"/categories/{category.id}/invitations",
        headers=get_auth_headers(client, "attacker@example.com", "mypassword123"),
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_list_category_invitations_unauthenticated(
    session: Session, client: TestClient
):
    """Test listing invitations without authentication"""
    organizer = create_user_in_db(
        session, email="organizer@example.com", password="mypassword123"
    )
    event = create_event_in_db(session, organizer=organizer)
    category = create_category_in_db(session, event=event)

    response = client.get(f"/categories/{category.id}/invitations")

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


# ---------------------------------------------------------------------------
# GET /categories/{category_id}/join_requests
# ---------------------------------------------------------------------------


def test_list_category_join_requests(session: Session, client: TestClient):
    """Test listing category join requests"""
    organizer = create_user_in_db(
        session, email="organizer@example.com", password="mypassword123"
    )
    joining_user = create_user_in_db(
        session, email="joining@example.com", password="mypassword123"
    )
    joining_player = create_player_in_db(session, user=joining_user)
    event = create_event_in_db(session, organizer=organizer)
    category = create_category_in_db(session, event=event)
    join_request = CategoryJoinRequest(
        category_id=category.id,
        player_id=joining_player.id,
        status=RequestStatus.PENDING,
    )
    session.add(join_request)
    session.commit()

    response = client.get(
        f"/categories/{category.id}/join_requests",
        headers=get_auth_headers(client, "organizer@example.com", "mypassword123"),
    )
    data = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert len(data) == 1
    assert data[0]["status"] == RequestStatus.PENDING.value
    assert data[0]["category"]["id"] == str(category.id)
    assert data[0]["player_id"] == str(joining_player.id)


def test_list_category_join_requests_empty(session: Session, client: TestClient):
    """Test listing join requests for a category without join requests"""
    organizer = create_user_in_db(
        session, email="organizer@example.com", password="mypassword123"
    )
    event = create_event_in_db(session, organizer=organizer)
    category = create_category_in_db(session, event=event)

    response = client.get(
        f"/categories/{category.id}/join_requests",
        headers=get_auth_headers(client, "organizer@example.com", "mypassword123"),
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == []


def test_list_category_join_requests_not_found(session: Session, client: TestClient):
    """Test listing join requests for a non-existent category"""
    create_user_in_db(session, email="organizer@example.com", password="mypassword123")

    response = client.get(
        "/categories/00000000-0000-0000-0000-000000000000/join_requests",
        headers=get_auth_headers(client, "organizer@example.com", "mypassword123"),
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_list_category_join_requests_unauthorized(session: Session, client: TestClient):
    """Test listing join requests without permission"""
    organizer = create_user_in_db(
        session, email="organizer@example.com", password="mypassword123"
    )
    create_user_in_db(session, email="attacker@example.com", password="mypassword123")
    event = create_event_in_db(session, organizer=organizer)
    category = create_category_in_db(session, event=event)

    response = client.get(
        f"/categories/{category.id}/join_requests",
        headers=get_auth_headers(client, "attacker@example.com", "mypassword123"),
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_list_category_join_requests_unauthenticated(
    session: Session, client: TestClient
):
    """Test listing join requests without authentication"""
    organizer = create_user_in_db(
        session, email="organizer@example.com", password="mypassword123"
    )
    event = create_event_in_db(session, organizer=organizer)
    category = create_category_in_db(session, event=event)

    response = client.get(f"/categories/{category.id}/join_requests")

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


# ---------------------------------------------------------------------------
# POST /categories/{category_id}/join_requests
# ---------------------------------------------------------------------------


def test_request_join_category(session: Session, client: TestClient):
    """Test requesting to join a category"""
    user = create_user_in_db(
        session, email="user@example.com", password="mypassword123"
    )
    create_player_in_db(session, user=user)
    event = create_event_in_db(session, organizer=user)
    category = create_category_in_db(session, event=event)

    response = client.post(
        f"/categories/{category.id}/join_requests",
        headers=get_auth_headers(client, "user@example.com", "mypassword123"),
    )

    assert response.status_code == status.HTTP_204_NO_CONTENT

    session.refresh(category)

    assert len(category.join_requests) == 1

    join_request = category.join_requests[0]
    assert join_request.status == RequestStatus.PENDING
    assert len(category.get_players_by_nickname()) == 0


def test_request_join_category_auto_accept(session: Session, client: TestClient):
    """Test requesting to join a category with auto-accept enabled"""
    organizer = create_user_in_db(
        session, email="organizer@example.com", password="mypassword123"
    )
    user = create_user_in_db(
        session, email="user@example.com", password="mypassword123"
    )
    player = create_player_in_db(session, user=user)
    event = create_event_in_db(session, organizer=organizer)
    category = create_category_in_db(
        session, event=event, auto_accept_join_requests=True
    )

    response = client.post(
        f"/categories/{category.id}/join_requests",
        headers=get_auth_headers(client, "user@example.com", "mypassword123"),
    )

    assert response.status_code == status.HTTP_204_NO_CONTENT
    session.refresh(category)
    assert len(category.get_players_by_nickname()) == 1
    assert category.get_players_by_nickname()[0] == player
    assert len(category.join_requests) == 0


def test_request_join_category_category_not_found(session: Session, client: TestClient):
    """Test requesting to join a non-existent category"""
    user = create_user_in_db(
        session, email="user@example.com", password="mypassword123"
    )
    create_player_in_db(session, user=user)

    response = client.post(
        "/categories/00000000-0000-0000-0000-000000000000/join_requests",
        headers=get_auth_headers(client, "user@example.com", "mypassword123"),
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_request_join_category_player_already_in_category(
    session: Session, client: TestClient
):
    """Test requesting to join a category when the player is already in it"""
    organizer = create_user_in_db(
        session, email="organizer@example.com", password="mypassword123"
    )
    user = create_user_in_db(
        session, email="user@example.com", password="mypassword123"
    )
    player = create_player_in_db(session, user=user)
    event = create_event_in_db(session, organizer=organizer)
    category = create_category_in_db(session, event=event)
    category.add_player(player)
    session.add(category)
    session.commit()

    response = client.post(
        f"/categories/{category.id}/join_requests",
        headers=get_auth_headers(client, "user@example.com", "mypassword123"),
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST


def test_request_join_category_existing_request_reopens(
    session: Session, client: TestClient
):
    """Test requesting to join a category with an existing declined request"""
    organizer = create_user_in_db(
        session, email="organizer@example.com", password="mypassword123"
    )
    user = create_user_in_db(
        session, email="user@example.com", password="mypassword123"
    )
    player = create_player_in_db(session, user=user)
    event = create_event_in_db(session, organizer=organizer)
    category = create_category_in_db(session, event=event)
    join_request = CategoryJoinRequest(
        category_id=category.id,
        player_id=player.id,
        status=RequestStatus.DECLINED,
    )
    session.add(join_request)
    session.commit()

    response = client.post(
        f"/categories/{category.id}/join_requests",
        headers=get_auth_headers(client, "user@example.com", "mypassword123"),
    )

    assert response.status_code == status.HTTP_204_NO_CONTENT

    session.refresh(join_request)
    assert join_request.status == RequestStatus.PENDING


# ---------------------------------------------------------------------------
# POST /categories/{category_id}/join_requests/{player_id}/accept
# ---------------------------------------------------------------------------


def test_accept_category_join_request(session: Session, client: TestClient):
    """Test accepting a category join request"""
    organizer = create_user_in_db(
        session, email="organizer@example.com", password="mypassword123"
    )
    user = create_user_in_db(
        session, email="user@example.com", password="mypassword123"
    )
    player = create_player_in_db(session, user=user)
    event = create_event_in_db(session, organizer=organizer)
    category = create_category_in_db(session, event=event)
    join_request = CategoryJoinRequest(
        category_id=category.id, player_id=player.id, status=RequestStatus.PENDING
    )
    session.add(join_request)
    session.commit()

    response = client.post(
        f"/categories/{category.id}/join_requests/{player.id}/accept",
        headers=get_auth_headers(client, "organizer@example.com", "mypassword123"),
    )

    assert response.status_code == status.HTTP_200_OK

    session.refresh(join_request)
    assert join_request.status == RequestStatus.ACCEPTED
    session.refresh(category)
    assert player in category.get_players_by_nickname()


def test_accept_category_join_request_unauthorized(
    session: Session, client: TestClient
):
    """Test accepting a category join request without permission"""
    organizer = create_user_in_db(
        session, email="organizer@example.com", password="mypassword123"
    )
    attacker = create_user_in_db(
        session, email="attacker@example.com", password="mypassword123"
    )
    player_user = create_user_in_db(
        session, email="player@example.com", password="mypassword123"
    )
    player = create_player_in_db(session, user=player_user)
    event = create_event_in_db(session, organizer=organizer)
    category = create_category_in_db(session, event=event)
    join_request = CategoryJoinRequest(category_id=category.id, player_id=player.id)
    session.add(join_request)
    session.commit()

    response = client.post(
        f"/categories/{category.id}/join_requests/{player.id}/accept",
        headers=get_auth_headers(client, attacker.email, "mypassword123"),
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN
    session.refresh(join_request)
    assert join_request.status == RequestStatus.PENDING


def test_accept_category_join_request_category_not_found(
    session: Session, client: TestClient
):
    """Test accepting a join request for a non-existent category"""
    organizer = create_user_in_db(
        session, email="organizer@example.com", password="mypassword123"
    )
    player_user = create_user_in_db(
        session, email="player@example.com", password="mypassword123"
    )
    player = create_player_in_db(session, user=player_user)
    create_event_in_db(session, organizer=organizer)

    response = client.post(
        f"/categories/00000000-0000-0000-0000-000000000000/join_requests/{player.id}/accept",
        headers=get_auth_headers(client, "organizer@example.com", "mypassword123"),
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_accept_category_join_request_player_not_found(
    session: Session, client: TestClient
):
    """Test accepting a join request for a non-existent player"""
    organizer = create_user_in_db(
        session, email="organizer@example.com", password="mypassword123"
    )
    event = create_event_in_db(session, organizer=organizer)
    category = create_category_in_db(session, event=event)

    response = client.post(
        f"/categories/{category.id}/join_requests/00000000-0000-0000-0000-000000000000/accept",
        headers=get_auth_headers(client, "organizer@example.com", "mypassword123"),
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_accept_category_join_request_player_already_in_category(
    session: Session, client: TestClient
):
    """Test accepting a join request when the player is already in the category"""
    organizer = create_user_in_db(
        session, email="organizer@example.com", password="mypassword123"
    )
    user = create_user_in_db(
        session, email="player@example.com", password="mypassword123"
    )
    player = create_player_in_db(session, user=user)
    event = create_event_in_db(session, organizer=organizer)
    category = create_category_in_db(session, event=event)
    category.add_player(player)
    session.add(category)
    session.commit()
    join_request = CategoryJoinRequest(category_id=category.id, player_id=player.id)
    session.add(join_request)
    session.commit()

    response = client.post(
        f"/categories/{category.id}/join_requests/{player.id}/accept",
        headers=get_auth_headers(client, "organizer@example.com", "mypassword123"),
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST


def test_accept_category_join_request_not_found(session: Session, client: TestClient):
    """Test accepting a non-existent join request"""
    organizer = create_user_in_db(
        session, email="organizer@example.com", password="mypassword123"
    )
    player_user = create_user_in_db(
        session, email="player@example.com", password="mypassword123"
    )
    player = create_player_in_db(session, user=player_user)
    event = create_event_in_db(session, organizer=organizer)
    category = create_category_in_db(session, event=event)

    response = client.post(
        f"/categories/{category.id}/join_requests/{player.id}/accept",
        headers=get_auth_headers(client, "organizer@example.com", "mypassword123"),
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_accept_category_join_request_not_pending_accepted(
    session: Session, client: TestClient
):
    """Test accepting a join request that is already accepted"""
    organizer = create_user_in_db(
        session, email="organizer@example.com", password="mypassword123"
    )
    user = create_user_in_db(
        session, email="player@example.com", password="mypassword123"
    )
    player = create_player_in_db(session, user=user)
    event = create_event_in_db(session, organizer=organizer)
    category = create_category_in_db(session, event=event)
    join_request = CategoryJoinRequest(
        category_id=category.id, player_id=player.id, status=RequestStatus.ACCEPTED
    )
    session.add(join_request)
    session.commit()

    response = client.post(
        f"/categories/{category.id}/join_requests/{player.id}/accept",
        headers=get_auth_headers(client, "organizer@example.com", "mypassword123"),
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST


def test_accept_category_join_request_not_pending_declined(
    session: Session, client: TestClient
):
    """Test accepting a join request that is declined"""
    organizer = create_user_in_db(
        session, email="organizer@example.com", password="mypassword123"
    )
    user = create_user_in_db(
        session, email="player@example.com", password="mypassword123"
    )
    player = create_player_in_db(session, user=user)
    event = create_event_in_db(session, organizer=organizer)
    category = create_category_in_db(session, event=event)
    join_request = CategoryJoinRequest(
        category_id=category.id, player_id=player.id, status=RequestStatus.DECLINED
    )
    session.add(join_request)
    session.commit()

    response = client.post(
        f"/categories/{category.id}/join_requests/{player.id}/accept",
        headers=get_auth_headers(client, "organizer@example.com", "mypassword123"),
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST


# ---------------------------------------------------------------------------
# POST /categories/{category_id}/join_requests/{player_id}/decline
# ---------------------------------------------------------------------------


def test_decline_category_join_request(session: Session, client: TestClient):
    """Test declining a category join request"""
    organizer = create_user_in_db(
        session, email="organizer@example.com", password="mypassword123"
    )
    user = create_user_in_db(
        session, email="user@example.com", password="mypassword123"
    )
    player = create_player_in_db(session, user=user)
    event = create_event_in_db(session, organizer=organizer)
    category = create_category_in_db(session, event=event)
    join_request = CategoryJoinRequest(
        category_id=category.id, player_id=player.id, status=RequestStatus.PENDING
    )
    session.add(join_request)
    session.commit()

    response = client.post(
        f"/categories/{category.id}/join_requests/{player.id}/decline",
        headers=get_auth_headers(client, "organizer@example.com", "mypassword123"),
    )

    assert response.status_code == status.HTTP_200_OK

    session.refresh(join_request)
    assert join_request.status == RequestStatus.DECLINED
    session.refresh(category)
    assert player not in category.get_players_by_nickname()


def test_decline_category_join_request_unauthorized(
    session: Session, client: TestClient
):
    """Test declining a category join request without permission"""
    organizer = create_user_in_db(
        session, email="organizer@example.com", password="mypassword123"
    )
    attacker = create_user_in_db(
        session, email="attacker@example.com", password="mypassword123"
    )
    player_user = create_user_in_db(
        session, email="player@example.com", password="mypassword123"
    )
    player = create_player_in_db(session, user=player_user)
    event = create_event_in_db(session, organizer=organizer)
    category = create_category_in_db(session, event=event)
    join_request = CategoryJoinRequest(category_id=category.id, player_id=player.id)
    session.add(join_request)
    session.commit()

    response = client.post(
        f"/categories/{category.id}/join_requests/{player.id}/decline",
        headers=get_auth_headers(client, attacker.email, "mypassword123"),
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN
    session.refresh(join_request)
    assert join_request.status == RequestStatus.PENDING


def test_decline_category_join_request_category_not_found(
    session: Session, client: TestClient
):
    """Test declining a join request for a non-existent category"""
    organizer = create_user_in_db(
        session, email="organizer@example.com", password="mypassword123"
    )
    player_user = create_user_in_db(
        session, email="player@example.com", password="mypassword123"
    )
    player = create_player_in_db(session, user=player_user)
    create_event_in_db(session, organizer=organizer)

    response = client.post(
        f"/categories/00000000-0000-0000-0000-000000000000/join_requests/{player.id}/decline",
        headers=get_auth_headers(client, "organizer@example.com", "mypassword123"),
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_decline_category_join_request_player_not_found(
    session: Session, client: TestClient
):
    """Test declining a join request for a non-existent player"""
    organizer = create_user_in_db(
        session, email="organizer@example.com", password="mypassword123"
    )
    event = create_event_in_db(session, organizer=organizer)
    category = create_category_in_db(session, event=event)

    response = client.post(
        f"/categories/{category.id}/join_requests/00000000-0000-0000-0000-000000000000/decline",
        headers=get_auth_headers(client, "organizer@example.com", "mypassword123"),
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_decline_category_join_request_player_already_in_category(
    session: Session, client: TestClient
):
    """Test declining a join request when the player is already in the category"""
    organizer = create_user_in_db(
        session, email="organizer@example.com", password="mypassword123"
    )
    user = create_user_in_db(
        session, email="player@example.com", password="mypassword123"
    )
    player = create_player_in_db(session, user=user)
    event = create_event_in_db(session, organizer=organizer)
    category = create_category_in_db(session, event=event)
    category.add_player(player)
    session.add(category)
    session.commit()
    join_request = CategoryJoinRequest(category_id=category.id, player_id=player.id)
    session.add(join_request)
    session.commit()

    response = client.post(
        f"/categories/{category.id}/join_requests/{player.id}/decline",
        headers=get_auth_headers(client, "organizer@example.com", "mypassword123"),
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST


def test_decline_category_join_request_not_found(session: Session, client: TestClient):
    """Test declining a non-existent join request"""
    organizer = create_user_in_db(
        session, email="organizer@example.com", password="mypassword123"
    )
    player_user = create_user_in_db(
        session, email="player@example.com", password="mypassword123"
    )
    player = create_player_in_db(session, user=player_user)
    event = create_event_in_db(session, organizer=organizer)
    category = create_category_in_db(session, event=event)

    response = client.post(
        f"/categories/{category.id}/join_requests/{player.id}/decline",
        headers=get_auth_headers(client, "organizer@example.com", "mypassword123"),
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_decline_category_join_request_not_pending_accepted(
    session: Session, client: TestClient
):
    """Test declining a join request that is already accepted"""
    organizer = create_user_in_db(
        session, email="organizer@example.com", password="mypassword123"
    )
    user = create_user_in_db(
        session, email="player@example.com", password="mypassword123"
    )
    player = create_player_in_db(session, user=user)
    event = create_event_in_db(session, organizer=organizer)
    category = create_category_in_db(session, event=event)
    join_request = CategoryJoinRequest(
        category_id=category.id, player_id=player.id, status=RequestStatus.ACCEPTED
    )
    session.add(join_request)
    session.commit()

    response = client.post(
        f"/categories/{category.id}/join_requests/{player.id}/decline",
        headers=get_auth_headers(client, "organizer@example.com", "mypassword123"),
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST


def test_decline_category_join_request_not_pending_declined(
    session: Session, client: TestClient
):
    """Test declining a join request that is already declined"""
    organizer = create_user_in_db(
        session, email="organizer@example.com", password="mypassword123"
    )
    user = create_user_in_db(
        session, email="player@example.com", password="mypassword123"
    )
    player = create_player_in_db(session, user=user)
    event = create_event_in_db(session, organizer=organizer)
    category = create_category_in_db(session, event=event)
    join_request = CategoryJoinRequest(
        category_id=category.id, player_id=player.id, status=RequestStatus.DECLINED
    )
    session.add(join_request)
    session.commit()

    response = client.post(
        f"/categories/{category.id}/join_requests/{player.id}/decline",
        headers=get_auth_headers(client, "organizer@example.com", "mypassword123"),
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST


# ---------------------------------------------------------------------------
# GET /categories/{category_id}/players
# ---------------------------------------------------------------------------


def test_list_players_in_category(session: Session, client: TestClient):
    event = create_event_in_db(session)
    category = create_category_in_db(session, event=event)
    player_a = create_player_in_db(session, nickname="PlayerA")
    player_b = create_player_in_db(session, nickname="PlayerB")
    category.add_player(player_a)
    category.add_player(player_b)
    session.add(category)
    session.commit()

    response = client.get(f"/categories/{category.id}/players")
    data = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert len(data) == 2
    nicknames = [link["player"]["nickname"] for link in data]
    assert "PlayerA" in nicknames
    assert "PlayerB" in nicknames


def test_list_players_in_category_empty(session: Session, client: TestClient):
    event = create_event_in_db(session)
    category = create_category_in_db(session, event=event)

    response = client.get(f"/categories/{category.id}/players")

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == []


def test_list_players_in_category_not_found(client: TestClient):
    response = client.get("/categories/00000000-0000-0000-0000-000000000000/players")

    assert response.status_code == status.HTTP_404_NOT_FOUND


# ---------------------------------------------------------------------------
# DELETE /categories/{category_id}/players/{player_id}
# ---------------------------------------------------------------------------


def test_remove_player_from_category(session: Session, client: TestClient):
    organizer = create_user_in_db(
        session, email="organizer@example.com", password="mypassword123"
    )
    event = create_event_in_db(session, organizer=organizer)
    category = create_category_in_db(session, event=event)
    player_a = create_player_in_db(session, nickname="PlayerA")
    player_b = create_player_in_db(session, nickname="PlayerB")
    category.add_player(player_a)
    category.add_player(player_b)
    session.add(category)
    session.commit()
    headers = get_auth_headers(client, "organizer@example.com", "mypassword123")

    response = client.delete(
        f"/categories/{category.id}/players/{player_a.id}",
        headers=headers,
    )
    data = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert len(data) == 1
    assert data[0]["player"]["nickname"] == "PlayerB"
    assert data[0]["has_paid_entry"] is False


def test_remove_player_from_category_when_player_not_in_category(
    session: Session, client: TestClient
):
    organizer = create_user_in_db(
        session, email="organizer@example.com", password="mypassword123"
    )
    event = create_event_in_db(session, organizer=organizer)
    category = create_category_in_db(session, event=event)
    player = create_player_in_db(session, nickname="PlayerA")
    headers = get_auth_headers(client, "organizer@example.com", "mypassword123")

    response = client.delete(
        f"/categories/{category.id}/players/{player.id}",
        headers=headers,
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_remove_player_from_category_category_not_found(
    session: Session, client: TestClient
):
    create_user_in_db(session, email="user@example.com", password="mypassword123")
    player = create_player_in_db(session, nickname="PlayerA")
    headers = get_auth_headers(client, "user@example.com", "mypassword123")

    response = client.delete(
        f"/categories/00000000-0000-0000-0000-000000000000/players/{player.id}",
        headers=headers,
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_remove_player_from_category_unauthorized(session: Session, client: TestClient):
    create_user_in_db(session, email="attacker@example.com", password="mypassword123")
    event = create_event_in_db(session)
    category = create_category_in_db(session, event=event)
    player = create_player_in_db(session, nickname="PlayerA")
    headers = get_auth_headers(client, "attacker@example.com", "mypassword123")

    response = client.delete(
        f"/categories/{category.id}/players/{player.id}",
        headers=headers,
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_remove_player_from_category_player_not_found(
    session: Session, client: TestClient
):
    organizer = create_user_in_db(
        session, email="organizer@example.com", password="mypassword123"
    )
    event = create_event_in_db(session, organizer=organizer)
    category = create_category_in_db(session, event=event)
    headers = get_auth_headers(client, "organizer@example.com", "mypassword123")

    response = client.delete(
        f"/categories/{category.id}/players/00000000-0000-0000-0000-000000000000",
        headers=headers,
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_remove_player_from_category_unauthenticated(
    session: Session, client: TestClient
):
    event = create_event_in_db(session)
    category = create_category_in_db(session, event=event)
    player = create_player_in_db(session, nickname="PlayerA")

    response = client.delete(f"/categories/{category.id}/players/{player.id}")

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


# ---------------------------------------------------------------------------
# PUT /categories/{category_id}/players/{player_id}
# ---------------------------------------------------------------------------


def test_update_player_in_category(session: Session, client: TestClient):
    organizer = create_user_in_db(
        session, email="organizer@example.com", password="mypassword123"
    )
    event = create_event_in_db(session, organizer=organizer)
    category = create_category_in_db(session, event=event)
    player = create_player_in_db(session, nickname="PlayerA")
    category.add_player(player)
    session.add(category)
    session.commit()
    headers = get_auth_headers(client, "organizer@example.com", "mypassword123")

    response = client.put(
        f"/categories/{category.id}/players/{player.id}",
        json={"has_paid_entry": True},
        headers=headers,
    )
    data = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert data["player"]["nickname"] == "PlayerA"
    assert data["has_paid_entry"] is True


def test_update_player_in_category_not_found(session: Session, client: TestClient):
    organizer = create_user_in_db(
        session, email="organizer@example.com", password="mypassword123"
    )
    event = create_event_in_db(session, organizer=organizer)
    category = create_category_in_db(session, event=event)
    headers = get_auth_headers(client, "organizer@example.com", "mypassword123")

    response = client.put(
        f"/categories/{category.id}/players/00000000-0000-0000-0000-000000000000",
        json={"has_paid_entry": True},
        headers=headers,
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND


# ---------------------------------------------------------------------------
# GET /categories/{category_id}/rounds
# ---------------------------------------------------------------------------


def test_list_rounds_in_category(session: Session, client: TestClient):
    event = create_event_in_db(session)
    category = create_category_in_db(session, event=event)
    create_round_in_db(session, category=category, name="Round A")
    create_round_in_db(session, category=category, name="Round B")
    create_round_in_db(session, category=category, name="Round C")

    response = client.get(f"/categories/{category.id}/rounds")

    assert response.status_code == status.HTTP_200_OK
    assert len(response.json()) == 3
    assert response.json()[0]["name"] == "Round A"
    assert response.json()[1]["name"] == "Round B"
    assert response.json()[2]["name"] == "Round C"


def test_list_rounds_in_category_correct_order(session: Session, client: TestClient):
    event = create_event_in_db(session)
    category = create_category_in_db(session, event=event)
    round_a = create_round_in_db(session, category=category, name="Round A")
    round_b = create_round_in_db(session, category=category, name="Round B")
    round_c = create_round_in_db(session, category=category, name="Round C")

    round_a.order_index = 1
    round_b.order_index = 2
    round_c.order_index = 0
    session.commit()

    response = client.get(f"/categories/{category.id}/rounds")

    assert response.status_code == status.HTTP_200_OK
    assert len(response.json()) == 3
    assert response.json()[0]["name"] == "Round C"
    assert response.json()[1]["name"] == "Round A"
    assert response.json()[2]["name"] == "Round B"


# ---------------------------------------------------------------------------
# PUT /categories/{category_id}/rounds/order
# ---------------------------------------------------------------------------


def test_change_round_order(session: Session, client: TestClient):
    organizer = create_user_in_db(
        session, email="organizer@example.com", password="mypassword123"
    )
    event = create_event_in_db(session, organizer=organizer)
    category = create_category_in_db(session, event=event)
    round_a = create_round_in_db(session, category=category, name="Round A")
    round_b = create_round_in_db(session, category=category, name="Round B")
    round_c = create_round_in_db(session, category=category, name="Round C")
    headers = get_auth_headers(client, "organizer@example.com", "mypassword123")

    response = client.put(
        f"/categories/{category.id}/rounds/order",
        json=[str(round_c.id), str(round_a.id), str(round_b.id)],
        headers=headers,
    )
    data = response.json()

    session.refresh(round_a)
    session.refresh(round_b)
    session.refresh(round_c)

    assert response.status_code == status.HTTP_200_OK
    assert len(data) == 3
    assert round_a.order_index == 1
    assert round_b.order_index == 2
    assert round_c.order_index == 0
    assert {round["id"]: round["order_index"] for round in data} == {
        str(round_a.id): 1,
        str(round_b.id): 2,
        str(round_c.id): 0,
    }


def test_change_round_order_as_super_admin(session: Session, client: TestClient):
    create_user_in_db(
        session,
        email="admin@example.com",
        password="mypassword123",
        is_super_admin=True,
    )
    event = create_event_in_db(session)
    category = create_category_in_db(session, event=event)
    round_a = create_round_in_db(session, category=category, name="Round A")
    round_b = create_round_in_db(session, category=category, name="Round B")
    headers = get_auth_headers(client, "admin@example.com", "mypassword123")

    response = client.put(
        f"/categories/{category.id}/rounds/order",
        json=[str(round_b.id), str(round_a.id)],
        headers=headers,
    )

    session.refresh(round_a)
    session.refresh(round_b)

    assert response.status_code == status.HTTP_200_OK
    assert round_a.order_index == 1
    assert round_b.order_index == 0


def test_change_round_order_category_not_found(session: Session, client: TestClient):
    create_user_in_db(session, email="user@example.com", password="mypassword123")
    headers = get_auth_headers(client, "user@example.com", "mypassword123")

    response = client.put(
        "/categories/00000000-0000-0000-0000-000000000000/rounds/order",
        json=["00000000-0000-0000-0000-000000000000"],
        headers=headers,
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_change_round_order_unauthorized(session: Session, client: TestClient):
    create_user_in_db(session, email="attacker@example.com", password="mypassword123")
    event = create_event_in_db(session)
    category = create_category_in_db(session, event=event)
    round_a = create_round_in_db(session, category=category)
    headers = get_auth_headers(client, "attacker@example.com", "mypassword123")

    response = client.put(
        f"/categories/{category.id}/rounds/order",
        json=[str(round_a.id)],
        headers=headers,
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_change_round_order_unauthenticated(session: Session, client: TestClient):
    event = create_event_in_db(session)
    category = create_category_in_db(session, event=event)
    round_a = create_round_in_db(session, category=category)

    response = client.put(
        f"/categories/{category.id}/rounds/order",
        json=[str(round_a.id)],
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_change_round_order_round_count_mismatch(session: Session, client: TestClient):
    organizer = create_user_in_db(
        session, email="organizer@example.com", password="mypassword123"
    )
    event = create_event_in_db(session, organizer=organizer)
    category = create_category_in_db(session, event=event)
    round_a = create_round_in_db(session, category=category)
    create_round_in_db(session, category=category)
    headers = get_auth_headers(client, "organizer@example.com", "mypassword123")

    response = client.put(
        f"/categories/{category.id}/rounds/order",
        json=[str(round_a.id)],
        headers=headers,
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST


def test_change_round_order_round_mismatch(session: Session, client: TestClient):
    organizer = create_user_in_db(
        session, email="organizer@example.com", password="mypassword123"
    )
    event = create_event_in_db(session, organizer=organizer)
    category = create_category_in_db(session, event=event)
    round_a = create_round_in_db(session, category=category)
    create_round_in_db(session, category=category)
    headers = get_auth_headers(client, "organizer@example.com", "mypassword123")

    response = client.put(
        f"/categories/{category.id}/rounds/order",
        json=[str(round_a.id), "00000000-0000-0000-0000-000000000000"],
        headers=headers,
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST


def test_change_round_order_round_repeated_round(session: Session, client: TestClient):
    organizer = create_user_in_db(
        session, email="organizer@example.com", password="mypassword123"
    )
    event = create_event_in_db(session, organizer=organizer)
    category = create_category_in_db(session, event=event)
    round_a = create_round_in_db(session, category=category)
    create_round_in_db(session, category=category)
    headers = get_auth_headers(client, "organizer@example.com", "mypassword123")

    response = client.put(
        f"/categories/{category.id}/rounds/order",
        json=[str(round_a.id), str(round_a.id)],
        headers=headers,
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST


def test_change_round_order_round_already_started(session: Session, client: TestClient):
    organizer = create_user_in_db(
        session, email="organizer@example.com", password="mypassword123"
    )
    event = create_event_in_db(session, organizer=organizer)
    category = create_category_in_db(session, event=event)

    round_a = create_round_in_db(session, category=category)
    round_b = create_round_in_db(session, category=category)

    round_a.state = RoundState.IN_PROGRESS
    session.commit()

    headers = get_auth_headers(client, "organizer@example.com", "mypassword123")

    response = client.put(
        f"/categories/{category.id}/rounds/order",
        json=[str(round_b.id), str(round_a.id)],
        headers=headers,
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST


def test_change_round_order_round_already_started_but_not_changing_order(
    session: Session, client: TestClient
):
    organizer = create_user_in_db(
        session, email="organizer@example.com", password="mypassword123"
    )
    event = create_event_in_db(session, organizer=organizer)
    category = create_category_in_db(session, event=event)

    round_a = create_round_in_db(session, category=category)
    round_b = create_round_in_db(session, category=category)
    round_c = create_round_in_db(session, category=category)

    round_a.state = RoundState.IN_PROGRESS
    session.commit()

    headers = get_auth_headers(client, "organizer@example.com", "mypassword123")

    response = client.put(
        f"/categories/{category.id}/rounds/order",
        json=[str(round_a.id), str(round_c.id), str(round_b.id)],
        headers=headers,
    )

    assert response.status_code == status.HTTP_200_OK
    assert [r["id"] for r in response.json()] == [
        str(round_a.id),
        str(round_c.id),
        str(round_b.id),
    ]
