from fastapi import status
from fastapi.testclient import TestClient
from sqlmodel import Session

from models.category_request import CategoryInvitation, RequestStatus
from models.round import RoundState
from tests.helpers import (
    create_category_in_db,
    create_player_in_db,
    create_round_in_db,
    create_tournament_in_db,
    create_user_in_db,
    get_auth_headers,
)

# ---------------------------------------------------------------------------
# GET /categories/
# ---------------------------------------------------------------------------


def test_list_categories(session: Session, client: TestClient):
    tournament = create_tournament_in_db(session)
    create_category_in_db(session, tournament=tournament, name="Category A")
    create_category_in_db(session, tournament=tournament, name="Category B")

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
    tournament = create_tournament_in_db(session)
    category = create_category_in_db(session, tournament=tournament, name="My Category")

    response = client.get(f"/categories/{category.id}")
    data = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert data["id"] == str(category.id)
    assert data["name"] == "My Category"
    assert data["tournament_id"] == str(tournament.id)


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
    tournament = create_tournament_in_db(session, organizer=organizer)
    headers = get_auth_headers(client, "organizer@example.com", "mypassword123")

    response = client.post(
        "/categories/",
        json={"name": "New Category", "tournament_id": str(tournament.id)},
        headers=headers,
    )
    data = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert data["id"] is not None
    assert data["name"] == "New Category"
    assert data["tournament_id"] == str(tournament.id)


def test_create_category_tournament_not_found(session: Session, client: TestClient):
    create_user_in_db(session, email="user@example.com", password="mypassword123")
    headers = get_auth_headers(client, "user@example.com", "mypassword123")

    response = client.post(
        "/categories/",
        json={
            "name": "New Category",
            "tournament_id": "00000000-0000-0000-0000-000000000000",
        },
        headers=headers,
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_create_category_unauthorized(session: Session, client: TestClient):
    create_user_in_db(session, email="attacker@example.com", password="mypassword123")
    tournament = create_tournament_in_db(session)
    headers = get_auth_headers(client, "attacker@example.com", "mypassword123")

    response = client.post(
        "/categories/",
        json={"name": "New Category", "tournament_id": str(tournament.id)},
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
    tournament = create_tournament_in_db(session)
    headers = get_auth_headers(client, "admin@example.com", "mypassword123")

    response = client.post(
        "/categories/",
        json={"name": "Admin Category", "tournament_id": str(tournament.id)},
        headers=headers,
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["name"] == "Admin Category"


def test_create_category_unauthenticated(session: Session, client: TestClient):
    tournament = create_tournament_in_db(session)

    response = client.post(
        "/categories/",
        json={"name": "New Category", "tournament_id": str(tournament.id)},
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_create_category_missing_name(session: Session, client: TestClient):
    organizer = create_user_in_db(
        session, email="organizer@example.com", password="mypassword123"
    )
    tournament = create_tournament_in_db(session, organizer=organizer)
    headers = get_auth_headers(client, "organizer@example.com", "mypassword123")

    response = client.post(
        "/categories/",
        json={"tournament_id": str(tournament.id)},
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
    tournament = create_tournament_in_db(session, organizer=organizer)
    category = create_category_in_db(session, tournament=tournament, name="Old Name")
    headers = get_auth_headers(client, "organizer@example.com", "mypassword123")

    response = client.patch(
        f"/categories/{category.id}",
        json={"name": "Updated Name"},
        headers=headers,
    )
    data = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert data["name"] == "Updated Name"
    assert data["tournament_id"] == str(tournament.id)


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
    tournament = create_tournament_in_db(session)
    category = create_category_in_db(session, tournament=tournament)
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
    tournament = create_tournament_in_db(session)
    category = create_category_in_db(session, tournament=tournament)
    headers = get_auth_headers(client, "admin@example.com", "mypassword123")

    response = client.patch(
        f"/categories/{category.id}",
        json={"name": "Admin Updated"},
        headers=headers,
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["name"] == "Admin Updated"


def test_update_category_unauthenticated(session: Session, client: TestClient):
    tournament = create_tournament_in_db(session)
    category = create_category_in_db(session, tournament=tournament)

    response = client.patch(f"/categories/{category.id}", json={"name": "Updated"})

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


# ---------------------------------------------------------------------------
# DELETE /categories/{category_id}
# ---------------------------------------------------------------------------


def test_delete_category_empty(session: Session, client: TestClient):
    organizer = create_user_in_db(
        session, email="organizer@example.com", password="mypassword123"
    )
    tournament = create_tournament_in_db(session, organizer=organizer)
    category = create_category_in_db(session, tournament=tournament)
    headers = get_auth_headers(client, "organizer@example.com", "mypassword123")

    response = client.delete(f"/categories/{category.id}", headers=headers)

    assert response.status_code == status.HTTP_204_NO_CONTENT

    get_response = client.get(f"/categories/{category.id}", headers=headers)
    assert get_response.status_code == status.HTTP_404_NOT_FOUND


def test_delete_category_with_a_started_round(session: Session, client: TestClient):
    create_user_in_db(session, email="organizer@example.com", password="mypassword123")
    headers = get_auth_headers(client, "organizer@example.com", "mypassword123")

    tournament = create_tournament_in_db(session)
    category = create_category_in_db(session, tournament=tournament)
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
    tournament = create_tournament_in_db(session)
    category = create_category_in_db(session, tournament=tournament)
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
    tournament = create_tournament_in_db(session)
    category = create_category_in_db(session, tournament=tournament)
    headers = get_auth_headers(client, "admin@example.com", "mypassword123")

    response = client.delete(f"/categories/{category.id}", headers=headers)

    assert response.status_code == status.HTTP_204_NO_CONTENT


def test_delete_category_unauthenticated(session: Session, client: TestClient):
    tournament = create_tournament_in_db(session)
    category = create_category_in_db(session, tournament=tournament)

    response = client.delete(f"/categories/{category.id}")

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_delete_tournament_cascade(session: Session, client: TestClient):
    organizer = create_user_in_db(
        session,
        email="organizer@example.com",
        password="mypassword123",
        is_super_admin=True,
    )
    headers = get_auth_headers(client, "organizer@example.com", "mypassword123")
    tournament = create_tournament_in_db(session, organizer=organizer)
    category = create_category_in_db(session, tournament=tournament)

    response = client.delete(f"/tournaments/{tournament.id}", headers=headers)

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
    tournament = create_tournament_in_db(session, organizer=organizer)
    category = create_category_in_db(session, tournament=tournament)
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
    tournament = create_tournament_in_db(session)
    category = create_category_in_db(session, tournament=tournament)
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
    tournament = create_tournament_in_db(session, organizer=organizer)
    category = create_category_in_db(session, tournament=tournament)
    headers = get_auth_headers(client, "organizer@example.com", "mypassword123")

    response = client.post(
        f"/categories/{category.id}/players/bulk",
        json=["00000000-0000-0000-0000-000000000000"],
        headers=headers,
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_bulk_add_players_unauthenticated(session: Session, client: TestClient):
    tournament = create_tournament_in_db(session)
    category = create_category_in_db(session, tournament=tournament)
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
    tournament = create_tournament_in_db(session, organizer=organizer_user)
    category = create_category_in_db(session, tournament=tournament)

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
    tournament = create_tournament_in_db(session, organizer=user)
    category = create_category_in_db(session, tournament=tournament)
    player = create_player_in_db(session, user=user)

    response = client.post(
        f"/categories/{category.id}/invitations/{player.id}/",
        headers=get_auth_headers(client, "user@example.com", "mypassword123"),
    )

    assert response.status_code == status.HTTP_204_NO_CONTENT

    session.refresh(category)
    assert len(category.players) == 1
    assert category.players[0].id == player.id


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
    tournament = create_tournament_in_db(session, organizer=user)
    category = create_category_in_db(session, tournament=tournament)

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
    tournament = create_tournament_in_db(session, organizer=user)
    category = create_category_in_db(session, tournament=tournament)
    player = create_player_in_db(session, user=None)

    response = client.post(
        f"/categories/{category.id}/invitations/{player.id}/",
        headers=get_auth_headers(client, "user@example.com", "mypassword123"),
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST


# ---------------------------------------------------------------------------
# POST /categories/{category_id}/invitations/accept
# ---------------------------------------------------------------------------


def test_accept_category_invitation(session: Session, client: TestClient):
    """Test accepting a category invitation"""
    user = create_user_in_db(
        session, email="user@example.com", password="mypassword123"
    )
    player = create_player_in_db(session, user=user)
    tournament = create_tournament_in_db(session, organizer=user)
    category = create_category_in_db(session, tournament=tournament)
    invitation = CategoryInvitation(category_id=category.id, player_id=player.id)
    session.add(invitation)
    session.commit()

    response = client.post(
        f"/categories/{category.id}/invitations/accept",
        headers=get_auth_headers(client, "user@example.com", "mypassword123"),
    )

    assert response.status_code == status.HTTP_200_OK

    session.refresh(category)
    assert len(category.players) == 1
    assert category.players[0].id == player.id


def test_accept_category_invitation_no_player(session: Session, client: TestClient):
    """Test accepting an invitation without an associated player"""
    user = create_user_in_db(
        session, email="user@example.com", password="mypassword123"
    )
    tournament = create_tournament_in_db(session, organizer=user)
    category = create_category_in_db(session, tournament=tournament)

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
    tournament = create_tournament_in_db(session, organizer=user)
    category = create_category_in_db(session, tournament=tournament)

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
    tournament = create_tournament_in_db(session, organizer=user)
    category = create_category_in_db(session, tournament=tournament)
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
# GET /categories/{category_id}/players
# ---------------------------------------------------------------------------


def test_list_players_in_category(session: Session, client: TestClient):
    tournament = create_tournament_in_db(session)
    category = create_category_in_db(session, tournament=tournament)
    player_a = create_player_in_db(session, nickname="PlayerA")
    player_b = create_player_in_db(session, nickname="PlayerB")
    category.players.append(player_a)
    category.players.append(player_b)
    session.add(category)
    session.commit()

    response = client.get(f"/categories/{category.id}/players")
    data = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert len(data) == 2
    nicknames = [p["nickname"] for p in data]
    assert "PlayerA" in nicknames
    assert "PlayerB" in nicknames


def test_list_players_in_category_empty(session: Session, client: TestClient):
    tournament = create_tournament_in_db(session)
    category = create_category_in_db(session, tournament=tournament)

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
    tournament = create_tournament_in_db(session, organizer=organizer)
    category = create_category_in_db(session, tournament=tournament)
    player_a = create_player_in_db(session, nickname="PlayerA")
    player_b = create_player_in_db(session, nickname="PlayerB")
    category.players.append(player_a)
    category.players.append(player_b)
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
    assert data[0]["nickname"] == "PlayerB"


def test_remove_player_from_category_when_player_not_in_category(
    session: Session, client: TestClient
):
    organizer = create_user_in_db(
        session, email="organizer@example.com", password="mypassword123"
    )
    tournament = create_tournament_in_db(session, organizer=organizer)
    category = create_category_in_db(session, tournament=tournament)
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
    tournament = create_tournament_in_db(session)
    category = create_category_in_db(session, tournament=tournament)
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
    tournament = create_tournament_in_db(session, organizer=organizer)
    category = create_category_in_db(session, tournament=tournament)
    headers = get_auth_headers(client, "organizer@example.com", "mypassword123")

    response = client.delete(
        f"/categories/{category.id}/players/00000000-0000-0000-0000-000000000000",
        headers=headers,
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_remove_player_from_category_unauthenticated(
    session: Session, client: TestClient
):
    tournament = create_tournament_in_db(session)
    category = create_category_in_db(session, tournament=tournament)
    player = create_player_in_db(session, nickname="PlayerA")

    response = client.delete(f"/categories/{category.id}/players/{player.id}")

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
