from fastapi import status
from fastapi.testclient import TestClient
from sqlmodel import Session

from models.round import RoundState
from models.tournament_invitation import (
    RequestStatus,
    TournamentInvitation,
    TournamentJoinRequest,
)
from tests.helpers import (
    create_event_in_db,
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
    event = create_event_in_db(session)
    create_tournament_in_db(session, event=event, name="Tournament A")
    create_tournament_in_db(session, event=event, name="Tournament B")

    response = client.get("/tournaments/")
    data = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert len(data) == 2
    names = [c["name"] for c in data]
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
    event = create_event_in_db(session)
    tournament = create_tournament_in_db(session, event=event, name="My Tournament")

    response = client.get(f"/tournaments/{tournament.id}")
    data = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert data["id"] == str(tournament.id)
    assert data["name"] == "My Tournament"
    assert data["event_id"] == str(event.id)


def test_get_tournament_not_found(client: TestClient):
    response = client.get("/tournaments/00000000-0000-0000-0000-000000000000")

    assert response.status_code == status.HTTP_404_NOT_FOUND


# ---------------------------------------------------------------------------
# POST /tournaments/
# ---------------------------------------------------------------------------


def test_create_tournament(session: Session, client: TestClient):
    organizer = create_user_in_db(
        session, email="organizer@example.com", password="mypassword123"
    )
    event = create_event_in_db(session, organizer=organizer)
    headers = get_auth_headers(client, "organizer@example.com", "mypassword123")

    response = client.post(
        "/tournaments/",
        json={"name": "New Tournament", "event_id": str(event.id)},
        headers=headers,
    )
    data = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert data["id"] is not None
    assert data["name"] == "New Tournament"
    assert data["event_id"] == str(event.id)


def test_create_tournament_event_not_found(session: Session, client: TestClient):
    create_user_in_db(session, email="user@example.com", password="mypassword123")
    headers = get_auth_headers(client, "user@example.com", "mypassword123")

    response = client.post(
        "/tournaments/",
        json={
            "name": "New Tournament",
            "event_id": "00000000-0000-0000-0000-000000000000",
        },
        headers=headers,
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_create_tournament_unauthorized(session: Session, client: TestClient):
    create_user_in_db(session, email="attacker@example.com", password="mypassword123")
    event = create_event_in_db(session)
    headers = get_auth_headers(client, "attacker@example.com", "mypassword123")

    response = client.post(
        "/tournaments/",
        json={"name": "New Tournament", "event_id": str(event.id)},
        headers=headers,
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_create_tournament_as_super_admin(session: Session, client: TestClient):
    create_user_in_db(
        session,
        email="admin@example.com",
        password="mypassword123",
        is_super_admin=True,
    )
    event = create_event_in_db(session)
    headers = get_auth_headers(client, "admin@example.com", "mypassword123")

    response = client.post(
        "/tournaments/",
        json={"name": "Admin Tournament", "event_id": str(event.id)},
        headers=headers,
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["name"] == "Admin Tournament"


def test_create_tournament_unauthenticated(session: Session, client: TestClient):
    event = create_event_in_db(session)

    response = client.post(
        "/tournaments/",
        json={"name": "New Tournament", "event_id": str(event.id)},
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_create_tournament_missing_name(session: Session, client: TestClient):
    organizer = create_user_in_db(
        session, email="organizer@example.com", password="mypassword123"
    )
    event = create_event_in_db(session, organizer=organizer)
    headers = get_auth_headers(client, "organizer@example.com", "mypassword123")

    response = client.post(
        "/tournaments/",
        json={"event_id": str(event.id)},
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
    event = create_event_in_db(session, organizer=organizer)
    tournament = create_tournament_in_db(session, event=event, name="Old Name")
    headers = get_auth_headers(client, "organizer@example.com", "mypassword123")

    response = client.patch(
        f"/tournaments/{tournament.id}",
        json={"name": "Updated Name"},
        headers=headers,
    )
    data = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert data["name"] == "Updated Name"
    assert data["event_id"] == str(event.id)


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
    event = create_event_in_db(session)
    tournament = create_tournament_in_db(session, event=event)
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
    event = create_event_in_db(session)
    tournament = create_tournament_in_db(session, event=event)
    headers = get_auth_headers(client, "admin@example.com", "mypassword123")

    response = client.patch(
        f"/tournaments/{tournament.id}",
        json={"name": "Admin Updated"},
        headers=headers,
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["name"] == "Admin Updated"


def test_update_tournament_unauthenticated(session: Session, client: TestClient):
    event = create_event_in_db(session)
    tournament = create_tournament_in_db(session, event=event)

    response = client.patch(f"/tournaments/{tournament.id}", json={"name": "Updated"})

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


# ---------------------------------------------------------------------------
# DELETE /tournaments/{tournament_id}
# ---------------------------------------------------------------------------


def test_delete_tournament_empty(session: Session, client: TestClient):
    organizer = create_user_in_db(
        session, email="organizer@example.com", password="mypassword123"
    )
    event = create_event_in_db(session, organizer=organizer)
    tournament = create_tournament_in_db(session, event=event)
    headers = get_auth_headers(client, "organizer@example.com", "mypassword123")

    response = client.delete(f"/tournaments/{tournament.id}", headers=headers)

    assert response.status_code == status.HTTP_204_NO_CONTENT

    get_response = client.get(f"/tournaments/{tournament.id}", headers=headers)
    assert get_response.status_code == status.HTTP_404_NOT_FOUND


def test_delete_tournament_with_a_started_round(session: Session, client: TestClient):
    create_user_in_db(session, email="organizer@example.com", password="mypassword123")
    headers = get_auth_headers(client, "organizer@example.com", "mypassword123")

    event = create_event_in_db(session)
    tournament = create_tournament_in_db(session, event=event)
    create_round_in_db(session, tournament=tournament, state=RoundState.IN_PROGRESS)

    response = client.delete(f"/tournaments/{tournament.id}", headers=headers)

    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_delete_tournament_not_found(session: Session, client: TestClient):
    create_user_in_db(session, email="user@example.com", password="mypassword123")
    headers = get_auth_headers(client, "user@example.com", "mypassword123")

    response = client.delete(
        "/tournaments/00000000-0000-0000-0000-000000000000",
        headers=headers,
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_delete_tournament_unauthorized(session: Session, client: TestClient):
    create_user_in_db(session, email="attacker@example.com", password="mypassword123")
    event = create_event_in_db(session)
    tournament = create_tournament_in_db(session, event=event)
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
    event = create_event_in_db(session)
    tournament = create_tournament_in_db(session, event=event)
    headers = get_auth_headers(client, "admin@example.com", "mypassword123")

    response = client.delete(f"/tournaments/{tournament.id}", headers=headers)

    assert response.status_code == status.HTTP_204_NO_CONTENT


def test_delete_tournament_unauthenticated(session: Session, client: TestClient):
    event = create_event_in_db(session)
    tournament = create_tournament_in_db(session, event=event)

    response = client.delete(f"/tournaments/{tournament.id}")

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
    tournament = create_tournament_in_db(session, event=event)

    response = client.delete(f"/events/{event.id}", headers=headers)

    assert response.status_code == status.HTTP_204_NO_CONTENT

    response = client.get(f"/tournaments/{tournament.id}")
    assert response.status_code == status.HTTP_404_NOT_FOUND


# ---------------------------------------------------------------------------
# POST /tournaments/{tournament_id}/players/bulk
# ---------------------------------------------------------------------------


def test_bulk_add_players_to_tournament(session: Session, client: TestClient):
    organizer = create_user_in_db(
        session, email="organizer@example.com", password="mypassword123"
    )
    event = create_event_in_db(session, organizer=organizer)
    tournament = create_tournament_in_db(session, event=event)
    player_a = create_player_in_db(session, nickname="PlayerA", guest_event=event)
    player_b = create_player_in_db(session, nickname="PlayerB", guest_event=event)
    headers = get_auth_headers(client, "organizer@example.com", "mypassword123")

    response = client.post(
        f"/tournaments/{tournament.id}/players/bulk",
        json=[str(player_a.id), str(player_b.id)],
        headers=headers,
    )
    data = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert len(data) == 2
    nicknames = [p["nickname"] for p in data]
    assert "PlayerA" in nicknames
    assert "PlayerB" in nicknames


def test_bulk_add_players_tournament_not_found(session: Session, client: TestClient):
    create_user_in_db(session, email="user@example.com", password="mypassword123")
    player = create_player_in_db(session, nickname="PlayerA")
    headers = get_auth_headers(client, "user@example.com", "mypassword123")

    response = client.post(
        "/tournaments/00000000-0000-0000-0000-000000000000/players/bulk",
        json=[str(player.id)],
        headers=headers,
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_bulk_add_players_unauthorized(session: Session, client: TestClient):
    create_user_in_db(session, email="attacker@example.com", password="mypassword123")
    event = create_event_in_db(session)
    tournament = create_tournament_in_db(session, event=event)
    player = create_player_in_db(session, nickname="PlayerA")
    headers = get_auth_headers(client, "attacker@example.com", "mypassword123")

    response = client.post(
        f"/tournaments/{tournament.id}/players/bulk",
        json=[str(player.id)],
        headers=headers,
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_bulk_add_players_player_not_found(session: Session, client: TestClient):
    organizer = create_user_in_db(
        session, email="organizer@example.com", password="mypassword123"
    )
    event = create_event_in_db(session, organizer=organizer)
    tournament = create_tournament_in_db(session, event=event)
    headers = get_auth_headers(client, "organizer@example.com", "mypassword123")

    response = client.post(
        f"/tournaments/{tournament.id}/players/bulk",
        json=["00000000-0000-0000-0000-000000000000"],
        headers=headers,
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_bulk_add_players_unauthenticated(session: Session, client: TestClient):
    event = create_event_in_db(session)
    tournament = create_tournament_in_db(session, event=event)
    player = create_player_in_db(session, nickname="PlayerA")

    response = client.post(
        f"/tournaments/{tournament.id}/players/bulk",
        json=[str(player.id)],
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


# ---------------------------------------------------------------------------
# POST /tournaments/{tournament_id}/invitations/{player_id}/
# ---------------------------------------------------------------------------


def test_invite_player_to_tournament(session: Session, client: TestClient):
    """Test inviting a player to a tournament"""
    organizer_user = create_user_in_db(
        session, email="organizer@example.com", password="mypassword123"
    )
    event = create_event_in_db(session, organizer=organizer_user)
    tournament = create_tournament_in_db(session, event=event)

    player_user = create_user_in_db(
        session, email="player@example.com", password="mypassword123"
    )
    player = create_player_in_db(session, nickname="PlayerA", user=player_user)

    headers = get_auth_headers(client, "organizer@example.com", "mypassword123")

    response = client.post(
        f"/tournaments/{tournament.id}/invitations/{player.id}/",
        headers=headers,
    )

    assert response.status_code == status.HTTP_204_NO_CONTENT

    session.refresh(tournament)
    assert len(tournament.invitations) == 1
    assert tournament.invitations[0].player_id == player.id


def test_invite_player_to_tournament_organizer(session: Session, client: TestClient):
    """Test inviting an organizer to their own tournament"""
    user = create_user_in_db(
        session, email="user@example.com", password="mypassword123"
    )
    event = create_event_in_db(session, organizer=user)
    tournament = create_tournament_in_db(session, event=event)
    player = create_player_in_db(session, user=user)

    response = client.post(
        f"/tournaments/{tournament.id}/invitations/{player.id}/",
        headers=get_auth_headers(client, "user@example.com", "mypassword123"),
    )

    assert response.status_code == status.HTTP_204_NO_CONTENT

    session.refresh(tournament)
    assert len(tournament.get_players_by_nickname()) == 1
    assert tournament.get_players_by_nickname()[0].id == player.id


def test_invite_player_to_tournament_tournament_not_found(
    session: Session, client: TestClient
):
    """Test inviting a player to a non-existent tournament"""
    user = create_user_in_db(
        session, email="user@example.com", password="mypassword123"
    )
    player = create_player_in_db(session, user=user)

    response = client.post(
        f"/tournaments/00000000-0000-0000-0000-000000000000/invitations/{player.id}/",
        headers=get_auth_headers(client, "user@example.com", "mypassword123"),
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_invite_player_to_tournament_player_not_found(
    session: Session, client: TestClient
):
    """Test inviting a non-existent player to a tournament"""
    user = create_user_in_db(
        session, email="user@example.com", password="mypassword123"
    )
    event = create_event_in_db(session, organizer=user)
    tournament = create_tournament_in_db(session, event=event)

    response = client.post(
        f"/tournaments/{tournament.id}/invitations/00000000-0000-0000-0000-000000000000/",
        headers=get_auth_headers(client, "user@example.com", "mypassword123"),
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_invite_player_to_tournament_player_not_registered(
    session: Session, client: TestClient
):
    """Test inviting a player without a user to a tournament"""
    user = create_user_in_db(
        session, email="user@example.com", password="mypassword123"
    )
    event = create_event_in_db(session, organizer=user)
    tournament = create_tournament_in_db(session, event=event)
    player = create_player_in_db(session, user=None)

    response = client.post(
        f"/tournaments/{tournament.id}/invitations/{player.id}/",
        headers=get_auth_headers(client, "user@example.com", "mypassword123"),
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST


def test_invite_player_to_tournament_player_already_in_tournament(
    session: Session, client: TestClient
):
    """Test inviting a player who is already in the tournament"""
    organizer = create_user_in_db(
        session, email="organizer@example.com", password="mypassword123"
    )
    player_user = create_user_in_db(
        session, email="player@example.com", password="mypassword123"
    )
    player = create_player_in_db(session, user=player_user)
    event = create_event_in_db(session, organizer=organizer)
    tournament = create_tournament_in_db(session, event=event)
    tournament.add_player(player)
    session.commit()

    response = client.post(
        f"/tournaments/{tournament.id}/invitations/{player.id}/",
        headers=get_auth_headers(client, "organizer@example.com", "mypassword123"),
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST


def test_invite_player_to_tournament_invitation_declined(
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
    tournament = create_tournament_in_db(session, event=event)
    invitation = TournamentInvitation(
        player_id=player.id,
        tournament_id=tournament.id,
        status=RequestStatus.DECLINED,
    )
    session.add(invitation)
    session.commit()

    response = client.post(
        f"/tournaments/{tournament.id}/invitations/{player.id}/",
        headers=get_auth_headers(client, "organizer@example.com", "mypassword123"),
    )

    assert response.status_code == status.HTTP_204_NO_CONTENT

    session.refresh(invitation)
    assert invitation.status == RequestStatus.PENDING


# ---------------------------------------------------------------------------
# POST /tournaments/{tournament_id}/invitations/accept
# ---------------------------------------------------------------------------


def test_accept_tournament_invitation(session: Session, client: TestClient):
    """Test accepting a tournament invitation"""
    user = create_user_in_db(
        session, email="user@example.com", password="mypassword123"
    )
    player = create_player_in_db(session, user=user)
    event = create_event_in_db(session, organizer=user)
    tournament = create_tournament_in_db(session, event=event)
    invitation = TournamentInvitation(tournament_id=tournament.id, player_id=player.id)
    session.add(invitation)
    session.commit()

    response = client.post(
        f"/tournaments/{tournament.id}/invitations/accept",
        headers=get_auth_headers(client, "user@example.com", "mypassword123"),
    )

    assert response.status_code == status.HTTP_200_OK

    session.refresh(tournament)
    assert len(tournament.get_players_by_nickname()) == 1
    assert tournament.get_players_by_nickname()[0].id == player.id


def test_accept_tournament_invitation_no_player(session: Session, client: TestClient):
    """Test accepting an invitation without an associated player"""
    user = create_user_in_db(
        session, email="user@example.com", password="mypassword123"
    )
    event = create_event_in_db(session, organizer=user)
    tournament = create_tournament_in_db(session, event=event)

    response = client.post(
        f"/tournaments/{tournament.id}/invitations/accept",
        headers=get_auth_headers(client, "user@example.com", "mypassword123"),
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST


def test_accept_tournament_invitation_tournament_not_found(
    session: Session, client: TestClient
):
    """Test accepting an invitation for a non-existent tournament"""
    user = create_user_in_db(
        session, email="user@example.com", password="mypassword123"
    )
    create_player_in_db(session, user=user)

    response = client.post(
        "/tournaments/00000000-0000-0000-0000-000000000000/invitations/accept",
        headers=get_auth_headers(client, "user@example.com", "mypassword123"),
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_accept_tournament_invitation_not_found(session: Session, client: TestClient):
    """Test accepting a non-existent invitation"""
    user = create_user_in_db(
        session, email="user@example.com", password="mypassword123"
    )
    create_player_in_db(session, user=user)
    event = create_event_in_db(session, organizer=user)
    tournament = create_tournament_in_db(session, event=event)

    response = client.post(
        f"/tournaments/{tournament.id}/invitations/accept",
        headers=get_auth_headers(client, "user@example.com", "mypassword123"),
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_accept_tournament_invitation_already_accepted(
    session: Session, client: TestClient
):
    """Test accepting an already accepted invitation"""
    user = create_user_in_db(
        session, email="user@example.com", password="mypassword123"
    )
    player = create_player_in_db(session, user=user)
    event = create_event_in_db(session, organizer=user)
    tournament = create_tournament_in_db(session, event=event)
    invitation = TournamentInvitation(
        tournament_id=tournament.id, player_id=player.id, status=RequestStatus.ACCEPTED
    )
    session.add(invitation)
    session.commit()

    response = client.post(
        f"/tournaments/{tournament.id}/invitations/accept",
        headers=get_auth_headers(client, "user@example.com", "mypassword123"),
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST


# ---------------------------------------------------------------------------
# POST /tournaments/{tournament_id}/invitations/decline
# ---------------------------------------------------------------------------


def test_decline_tournament_invitation(session: Session, client: TestClient):
    """Test declining a tournament invitation"""
    user = create_user_in_db(
        session, email="user@example.com", password="mypassword123"
    )
    player = create_player_in_db(session, user=user)
    event = create_event_in_db(session, organizer=user)
    tournament = create_tournament_in_db(session, event=event)
    invitation = TournamentInvitation(tournament_id=tournament.id, player_id=player.id)
    session.add(invitation)
    session.commit()

    response = client.post(
        f"/tournaments/{tournament.id}/invitations/decline",
        headers=get_auth_headers(client, "user@example.com", "mypassword123"),
    )

    assert response.status_code == status.HTTP_200_OK

    session.refresh(invitation)
    assert invitation.status == RequestStatus.DECLINED
    session.refresh(tournament)
    assert len(tournament.get_players_by_nickname()) == 0


def test_decline_tournament_invitation_no_player(session: Session, client: TestClient):
    """Test declining an invitation without an associated player"""
    user = create_user_in_db(
        session, email="user@example.com", password="mypassword123"
    )
    event = create_event_in_db(session, organizer=user)
    tournament = create_tournament_in_db(session, event=event)

    response = client.post(
        f"/tournaments/{tournament.id}/invitations/decline",
        headers=get_auth_headers(client, "user@example.com", "mypassword123"),
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST


def test_decline_tournament_invitation_tournament_not_found(
    session: Session, client: TestClient
):
    """Test declining an invitation for a non-existent tournament"""
    user = create_user_in_db(
        session, email="user@example.com", password="mypassword123"
    )
    create_player_in_db(session, user=user)

    response = client.post(
        "/tournaments/00000000-0000-0000-0000-000000000000/invitations/decline",
        headers=get_auth_headers(client, "user@example.com", "mypassword123"),
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_decline_tournament_invitation_not_found(session: Session, client: TestClient):
    """Test declining a non-existent invitation"""
    user = create_user_in_db(
        session, email="user@example.com", password="mypassword123"
    )
    create_player_in_db(session, user=user)
    event = create_event_in_db(session, organizer=user)
    tournament = create_tournament_in_db(session, event=event)

    response = client.post(
        f"/tournaments/{tournament.id}/invitations/decline",
        headers=get_auth_headers(client, "user@example.com", "mypassword123"),
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_decline_tournament_invitation_already_declined(
    session: Session, client: TestClient
):
    """Test declining an already declined invitation"""
    user = create_user_in_db(
        session, email="user@example.com", password="mypassword123"
    )
    player = create_player_in_db(session, user=user)
    event = create_event_in_db(session, organizer=user)
    tournament = create_tournament_in_db(session, event=event)
    invitation = TournamentInvitation(
        tournament_id=tournament.id, player_id=player.id, status=RequestStatus.DECLINED
    )
    session.add(invitation)
    session.commit()

    response = client.post(
        f"/tournaments/{tournament.id}/invitations/decline",
        headers=get_auth_headers(client, "user@example.com", "mypassword123"),
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST


def test_decline_tournament_invitation_already_accepted(
    session: Session, client: TestClient
):
    """Test declining an already accepted invitation"""
    user = create_user_in_db(
        session, email="user@example.com", password="mypassword123"
    )
    player = create_player_in_db(session, user=user)
    event = create_event_in_db(session, organizer=user)
    tournament = create_tournament_in_db(session, event=event)
    invitation = TournamentInvitation(
        tournament_id=tournament.id, player_id=player.id, status=RequestStatus.ACCEPTED
    )
    session.add(invitation)
    session.commit()

    response = client.post(
        f"/tournaments/{tournament.id}/invitations/decline",
        headers=get_auth_headers(client, "user@example.com", "mypassword123"),
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST


# ---------------------------------------------------------------------------
# GET /tournaments/{tournament_id}/invitations
# ---------------------------------------------------------------------------


def test_list_tournament_invitations(session: Session, client: TestClient):
    """Test listing tournament invitations"""
    organizer = create_user_in_db(
        session, email="organizer@example.com", password="mypassword123"
    )
    invited_user = create_user_in_db(
        session, email="invited@example.com", password="mypassword123"
    )
    invited_player = create_player_in_db(session, user=invited_user)
    event = create_event_in_db(session, organizer=organizer)
    tournament = create_tournament_in_db(session, event=event)
    invitation = TournamentInvitation(
        tournament_id=tournament.id,
        player_id=invited_player.id,
        status=RequestStatus.PENDING,
    )
    session.add(invitation)
    session.commit()

    response = client.get(
        f"/tournaments/{tournament.id}/invitations",
        headers=get_auth_headers(client, "organizer@example.com", "mypassword123"),
    )
    data = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert len(data) == 1
    assert data[0]["status"] == RequestStatus.PENDING.value
    assert data[0]["tournament_id"] == str(tournament.id)
    assert data[0]["player"]["id"] == str(invited_player.id)


def test_list_tournament_invitations_empty(session: Session, client: TestClient):
    """Test listing invitations for a tournament without invitations"""
    organizer = create_user_in_db(
        session, email="organizer@example.com", password="mypassword123"
    )
    event = create_event_in_db(session, organizer=organizer)
    tournament = create_tournament_in_db(session, event=event)

    response = client.get(
        f"/tournaments/{tournament.id}/invitations",
        headers=get_auth_headers(client, "organizer@example.com", "mypassword123"),
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == []


def test_list_tournament_invitations_not_found(session: Session, client: TestClient):
    """Test listing invitations for a non-existent tournament"""
    create_user_in_db(session, email="organizer@example.com", password="mypassword123")

    response = client.get(
        "/tournaments/00000000-0000-0000-0000-000000000000/invitations",
        headers=get_auth_headers(client, "organizer@example.com", "mypassword123"),
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_list_tournament_invitations_unauthorized(session: Session, client: TestClient):
    """Test listing invitations without permission"""
    organizer = create_user_in_db(
        session, email="organizer@example.com", password="mypassword123"
    )
    create_user_in_db(session, email="attacker@example.com", password="mypassword123")
    event = create_event_in_db(session, organizer=organizer)
    tournament = create_tournament_in_db(session, event=event)

    response = client.get(
        f"/tournaments/{tournament.id}/invitations",
        headers=get_auth_headers(client, "attacker@example.com", "mypassword123"),
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_list_tournament_invitations_unauthenticated(
    session: Session, client: TestClient
):
    """Test listing invitations without authentication"""
    organizer = create_user_in_db(
        session, email="organizer@example.com", password="mypassword123"
    )
    event = create_event_in_db(session, organizer=organizer)
    tournament = create_tournament_in_db(session, event=event)

    response = client.get(f"/tournaments/{tournament.id}/invitations")

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


# ---------------------------------------------------------------------------
# GET /tournaments/{tournament_id}/join_requests
# ---------------------------------------------------------------------------


def test_list_tournament_join_requests(session: Session, client: TestClient):
    """Test listing tournament join requests"""
    organizer = create_user_in_db(
        session, email="organizer@example.com", password="mypassword123"
    )
    joining_user = create_user_in_db(
        session, email="joining@example.com", password="mypassword123"
    )
    joining_player = create_player_in_db(session, user=joining_user)
    event = create_event_in_db(session, organizer=organizer)
    tournament = create_tournament_in_db(session, event=event)
    join_request = TournamentJoinRequest(
        tournament_id=tournament.id,
        player_id=joining_player.id,
        status=RequestStatus.PENDING,
    )
    session.add(join_request)
    session.commit()

    response = client.get(
        f"/tournaments/{tournament.id}/join_requests",
        headers=get_auth_headers(client, "organizer@example.com", "mypassword123"),
    )
    data = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert len(data) == 1
    assert data[0]["status"] == RequestStatus.PENDING.value
    assert data[0]["tournament"]["id"] == str(tournament.id)
    assert data[0]["player_id"] == str(joining_player.id)


def test_list_tournament_join_requests_empty(session: Session, client: TestClient):
    """Test listing join requests for a tournament without join requests"""
    organizer = create_user_in_db(
        session, email="organizer@example.com", password="mypassword123"
    )
    event = create_event_in_db(session, organizer=organizer)
    tournament = create_tournament_in_db(session, event=event)

    response = client.get(
        f"/tournaments/{tournament.id}/join_requests",
        headers=get_auth_headers(client, "organizer@example.com", "mypassword123"),
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == []


def test_list_tournament_join_requests_not_found(session: Session, client: TestClient):
    """Test listing join requests for a non-existent tournament"""
    create_user_in_db(session, email="organizer@example.com", password="mypassword123")

    response = client.get(
        "/tournaments/00000000-0000-0000-0000-000000000000/join_requests",
        headers=get_auth_headers(client, "organizer@example.com", "mypassword123"),
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_list_tournament_join_requests_unauthorized(
    session: Session, client: TestClient
):
    """Test listing join requests without permission"""
    organizer = create_user_in_db(
        session, email="organizer@example.com", password="mypassword123"
    )
    create_user_in_db(session, email="attacker@example.com", password="mypassword123")
    event = create_event_in_db(session, organizer=organizer)
    tournament = create_tournament_in_db(session, event=event)

    response = client.get(
        f"/tournaments/{tournament.id}/join_requests",
        headers=get_auth_headers(client, "attacker@example.com", "mypassword123"),
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_list_tournament_join_requests_unauthenticated(
    session: Session, client: TestClient
):
    """Test listing join requests without authentication"""
    organizer = create_user_in_db(
        session, email="organizer@example.com", password="mypassword123"
    )
    event = create_event_in_db(session, organizer=organizer)
    tournament = create_tournament_in_db(session, event=event)

    response = client.get(f"/tournaments/{tournament.id}/join_requests")

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


# ---------------------------------------------------------------------------
# POST /tournaments/{tournament_id}/join_requests
# ---------------------------------------------------------------------------


def test_request_join_tournament(session: Session, client: TestClient):
    """Test requesting to join a tournament"""
    user = create_user_in_db(
        session, email="user@example.com", password="mypassword123"
    )
    create_player_in_db(session, user=user)
    event = create_event_in_db(session, organizer=user)
    tournament = create_tournament_in_db(session, event=event)

    response = client.post(
        f"/tournaments/{tournament.id}/join_requests",
        headers=get_auth_headers(client, "user@example.com", "mypassword123"),
    )

    assert response.status_code == status.HTTP_204_NO_CONTENT

    session.refresh(tournament)

    assert len(tournament.join_requests) == 1

    join_request = tournament.join_requests[0]
    assert join_request.status == RequestStatus.PENDING
    assert len(tournament.get_players_by_nickname()) == 0


def test_request_join_tournament_auto_accept(session: Session, client: TestClient):
    """Test requesting to join a tournament with auto-accept enabled"""
    organizer = create_user_in_db(
        session, email="organizer@example.com", password="mypassword123"
    )
    user = create_user_in_db(
        session, email="user@example.com", password="mypassword123"
    )
    player = create_player_in_db(session, user=user)
    event = create_event_in_db(session, organizer=organizer)
    tournament = create_tournament_in_db(
        session, event=event, auto_accept_join_requests=True
    )

    response = client.post(
        f"/tournaments/{tournament.id}/join_requests",
        headers=get_auth_headers(client, "user@example.com", "mypassword123"),
    )

    assert response.status_code == status.HTTP_204_NO_CONTENT
    session.refresh(tournament)
    assert len(tournament.get_players_by_nickname()) == 1
    assert tournament.get_players_by_nickname()[0] == player
    assert len(tournament.join_requests) == 0


def test_request_join_tournament_tournament_not_found(
    session: Session, client: TestClient
):
    """Test requesting to join a non-existent tournament"""
    user = create_user_in_db(
        session, email="user@example.com", password="mypassword123"
    )
    create_player_in_db(session, user=user)

    response = client.post(
        "/tournaments/00000000-0000-0000-0000-000000000000/join_requests",
        headers=get_auth_headers(client, "user@example.com", "mypassword123"),
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_request_join_tournament_player_already_in_tournament(
    session: Session, client: TestClient
):
    """Test requesting to join a tournament when the player is already in it"""
    organizer = create_user_in_db(
        session, email="organizer@example.com", password="mypassword123"
    )
    user = create_user_in_db(
        session, email="user@example.com", password="mypassword123"
    )
    player = create_player_in_db(session, user=user)
    event = create_event_in_db(session, organizer=organizer)
    tournament = create_tournament_in_db(session, event=event)
    tournament.add_player(player)
    session.add(tournament)
    session.commit()

    response = client.post(
        f"/tournaments/{tournament.id}/join_requests",
        headers=get_auth_headers(client, "user@example.com", "mypassword123"),
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST


def test_request_join_tournament_existing_request_reopens(
    session: Session, client: TestClient
):
    """Test requesting to join a tournament with an existing declined request"""
    organizer = create_user_in_db(
        session, email="organizer@example.com", password="mypassword123"
    )
    user = create_user_in_db(
        session, email="user@example.com", password="mypassword123"
    )
    player = create_player_in_db(session, user=user)
    event = create_event_in_db(session, organizer=organizer)
    tournament = create_tournament_in_db(session, event=event)
    join_request = TournamentJoinRequest(
        tournament_id=tournament.id,
        player_id=player.id,
        status=RequestStatus.DECLINED,
    )
    session.add(join_request)
    session.commit()

    response = client.post(
        f"/tournaments/{tournament.id}/join_requests",
        headers=get_auth_headers(client, "user@example.com", "mypassword123"),
    )

    assert response.status_code == status.HTTP_204_NO_CONTENT

    session.refresh(join_request)
    assert join_request.status == RequestStatus.PENDING


# ---------------------------------------------------------------------------
# POST /tournaments/{tournament_id}/join_requests/{player_id}/accept
# ---------------------------------------------------------------------------


def test_accept_tournament_join_request(session: Session, client: TestClient):
    """Test accepting a tournament join request"""
    organizer = create_user_in_db(
        session, email="organizer@example.com", password="mypassword123"
    )
    user = create_user_in_db(
        session, email="user@example.com", password="mypassword123"
    )
    player = create_player_in_db(session, user=user)
    event = create_event_in_db(session, organizer=organizer)
    tournament = create_tournament_in_db(session, event=event)
    join_request = TournamentJoinRequest(
        tournament_id=tournament.id, player_id=player.id, status=RequestStatus.PENDING
    )
    session.add(join_request)
    session.commit()

    response = client.post(
        f"/tournaments/{tournament.id}/join_requests/{player.id}/accept",
        headers=get_auth_headers(client, "organizer@example.com", "mypassword123"),
    )

    assert response.status_code == status.HTTP_200_OK

    session.refresh(join_request)
    assert join_request.status == RequestStatus.ACCEPTED
    session.refresh(tournament)
    assert player in tournament.get_players_by_nickname()


def test_accept_tournament_join_request_unauthorized(
    session: Session, client: TestClient
):
    """Test accepting a tournament join request without permission"""
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
    tournament = create_tournament_in_db(session, event=event)
    join_request = TournamentJoinRequest(
        tournament_id=tournament.id, player_id=player.id
    )
    session.add(join_request)
    session.commit()

    response = client.post(
        f"/tournaments/{tournament.id}/join_requests/{player.id}/accept",
        headers=get_auth_headers(client, attacker.email, "mypassword123"),
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN
    session.refresh(join_request)
    assert join_request.status == RequestStatus.PENDING


def test_accept_tournament_join_request_tournament_not_found(
    session: Session, client: TestClient
):
    """Test accepting a join request for a non-existent tournament"""
    organizer = create_user_in_db(
        session, email="organizer@example.com", password="mypassword123"
    )
    player_user = create_user_in_db(
        session, email="player@example.com", password="mypassword123"
    )
    player = create_player_in_db(session, user=player_user)
    create_event_in_db(session, organizer=organizer)

    response = client.post(
        f"/tournaments/00000000-0000-0000-0000-000000000000/join_requests/{player.id}/accept",
        headers=get_auth_headers(client, "organizer@example.com", "mypassword123"),
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_accept_tournament_join_request_player_not_found(
    session: Session, client: TestClient
):
    """Test accepting a join request for a non-existent player"""
    organizer = create_user_in_db(
        session, email="organizer@example.com", password="mypassword123"
    )
    event = create_event_in_db(session, organizer=organizer)
    tournament = create_tournament_in_db(session, event=event)

    response = client.post(
        f"/tournaments/{tournament.id}/join_requests/00000000-0000-0000-0000-000000000000/accept",
        headers=get_auth_headers(client, "organizer@example.com", "mypassword123"),
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_accept_tournament_join_request_player_already_in_tournament(
    session: Session, client: TestClient
):
    """Test accepting a join request when the player is already in the tournament"""
    organizer = create_user_in_db(
        session, email="organizer@example.com", password="mypassword123"
    )
    user = create_user_in_db(
        session, email="player@example.com", password="mypassword123"
    )
    player = create_player_in_db(session, user=user)
    event = create_event_in_db(session, organizer=organizer)
    tournament = create_tournament_in_db(session, event=event)
    tournament.add_player(player)
    session.add(tournament)
    session.commit()
    join_request = TournamentJoinRequest(
        tournament_id=tournament.id, player_id=player.id
    )
    session.add(join_request)
    session.commit()

    response = client.post(
        f"/tournaments/{tournament.id}/join_requests/{player.id}/accept",
        headers=get_auth_headers(client, "organizer@example.com", "mypassword123"),
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST


def test_accept_tournament_join_request_not_found(session: Session, client: TestClient):
    """Test accepting a non-existent join request"""
    organizer = create_user_in_db(
        session, email="organizer@example.com", password="mypassword123"
    )
    player_user = create_user_in_db(
        session, email="player@example.com", password="mypassword123"
    )
    player = create_player_in_db(session, user=player_user)
    event = create_event_in_db(session, organizer=organizer)
    tournament = create_tournament_in_db(session, event=event)

    response = client.post(
        f"/tournaments/{tournament.id}/join_requests/{player.id}/accept",
        headers=get_auth_headers(client, "organizer@example.com", "mypassword123"),
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_accept_tournament_join_request_not_pending_accepted(
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
    tournament = create_tournament_in_db(session, event=event)
    join_request = TournamentJoinRequest(
        tournament_id=tournament.id, player_id=player.id, status=RequestStatus.ACCEPTED
    )
    session.add(join_request)
    session.commit()

    response = client.post(
        f"/tournaments/{tournament.id}/join_requests/{player.id}/accept",
        headers=get_auth_headers(client, "organizer@example.com", "mypassword123"),
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST


def test_accept_tournament_join_request_not_pending_declined(
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
    tournament = create_tournament_in_db(session, event=event)
    join_request = TournamentJoinRequest(
        tournament_id=tournament.id, player_id=player.id, status=RequestStatus.DECLINED
    )
    session.add(join_request)
    session.commit()

    response = client.post(
        f"/tournaments/{tournament.id}/join_requests/{player.id}/accept",
        headers=get_auth_headers(client, "organizer@example.com", "mypassword123"),
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST


# ---------------------------------------------------------------------------
# POST /tournaments/{tournament_id}/join_requests/{player_id}/decline
# ---------------------------------------------------------------------------


def test_decline_tournament_join_request(session: Session, client: TestClient):
    """Test declining a tournament join request"""
    organizer = create_user_in_db(
        session, email="organizer@example.com", password="mypassword123"
    )
    user = create_user_in_db(
        session, email="user@example.com", password="mypassword123"
    )
    player = create_player_in_db(session, user=user)
    event = create_event_in_db(session, organizer=organizer)
    tournament = create_tournament_in_db(session, event=event)
    join_request = TournamentJoinRequest(
        tournament_id=tournament.id, player_id=player.id, status=RequestStatus.PENDING
    )
    session.add(join_request)
    session.commit()

    response = client.post(
        f"/tournaments/{tournament.id}/join_requests/{player.id}/decline",
        headers=get_auth_headers(client, "organizer@example.com", "mypassword123"),
    )

    assert response.status_code == status.HTTP_200_OK

    session.refresh(join_request)
    assert join_request.status == RequestStatus.DECLINED
    session.refresh(tournament)
    assert player not in tournament.get_players_by_nickname()


def test_decline_tournament_join_request_unauthorized(
    session: Session, client: TestClient
):
    """Test declining a tournament join request without permission"""
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
    tournament = create_tournament_in_db(session, event=event)
    join_request = TournamentJoinRequest(
        tournament_id=tournament.id, player_id=player.id
    )
    session.add(join_request)
    session.commit()

    response = client.post(
        f"/tournaments/{tournament.id}/join_requests/{player.id}/decline",
        headers=get_auth_headers(client, attacker.email, "mypassword123"),
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN
    session.refresh(join_request)
    assert join_request.status == RequestStatus.PENDING


def test_decline_tournament_join_request_tournament_not_found(
    session: Session, client: TestClient
):
    """Test declining a join request for a non-existent tournament"""
    organizer = create_user_in_db(
        session, email="organizer@example.com", password="mypassword123"
    )
    player_user = create_user_in_db(
        session, email="player@example.com", password="mypassword123"
    )
    player = create_player_in_db(session, user=player_user)
    create_event_in_db(session, organizer=organizer)

    response = client.post(
        f"/tournaments/00000000-0000-0000-0000-000000000000/join_requests/{player.id}/decline",
        headers=get_auth_headers(client, "organizer@example.com", "mypassword123"),
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_decline_tournament_join_request_player_not_found(
    session: Session, client: TestClient
):
    """Test declining a join request for a non-existent player"""
    organizer = create_user_in_db(
        session, email="organizer@example.com", password="mypassword123"
    )
    event = create_event_in_db(session, organizer=organizer)
    tournament = create_tournament_in_db(session, event=event)

    response = client.post(
        f"/tournaments/{tournament.id}/join_requests/00000000-0000-0000-0000-000000000000/decline",
        headers=get_auth_headers(client, "organizer@example.com", "mypassword123"),
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_decline_tournament_join_request_player_already_in_tournament(
    session: Session, client: TestClient
):
    """Test declining a join request when the player is already in the tournament"""
    organizer = create_user_in_db(
        session, email="organizer@example.com", password="mypassword123"
    )
    user = create_user_in_db(
        session, email="player@example.com", password="mypassword123"
    )
    player = create_player_in_db(session, user=user)
    event = create_event_in_db(session, organizer=organizer)
    tournament = create_tournament_in_db(session, event=event)
    tournament.add_player(player)
    session.add(tournament)
    session.commit()
    join_request = TournamentJoinRequest(
        tournament_id=tournament.id, player_id=player.id
    )
    session.add(join_request)
    session.commit()

    response = client.post(
        f"/tournaments/{tournament.id}/join_requests/{player.id}/decline",
        headers=get_auth_headers(client, "organizer@example.com", "mypassword123"),
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST


def test_decline_tournament_join_request_not_found(
    session: Session, client: TestClient
):
    """Test declining a non-existent join request"""
    organizer = create_user_in_db(
        session, email="organizer@example.com", password="mypassword123"
    )
    player_user = create_user_in_db(
        session, email="player@example.com", password="mypassword123"
    )
    player = create_player_in_db(session, user=player_user)
    event = create_event_in_db(session, organizer=organizer)
    tournament = create_tournament_in_db(session, event=event)

    response = client.post(
        f"/tournaments/{tournament.id}/join_requests/{player.id}/decline",
        headers=get_auth_headers(client, "organizer@example.com", "mypassword123"),
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_decline_tournament_join_request_not_pending_accepted(
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
    tournament = create_tournament_in_db(session, event=event)
    join_request = TournamentJoinRequest(
        tournament_id=tournament.id, player_id=player.id, status=RequestStatus.ACCEPTED
    )
    session.add(join_request)
    session.commit()

    response = client.post(
        f"/tournaments/{tournament.id}/join_requests/{player.id}/decline",
        headers=get_auth_headers(client, "organizer@example.com", "mypassword123"),
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST


def test_decline_tournament_join_request_not_pending_declined(
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
    tournament = create_tournament_in_db(session, event=event)
    join_request = TournamentJoinRequest(
        tournament_id=tournament.id, player_id=player.id, status=RequestStatus.DECLINED
    )
    session.add(join_request)
    session.commit()

    response = client.post(
        f"/tournaments/{tournament.id}/join_requests/{player.id}/decline",
        headers=get_auth_headers(client, "organizer@example.com", "mypassword123"),
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST


# ---------------------------------------------------------------------------
# GET /tournaments/{tournament_id}/players
# ---------------------------------------------------------------------------


def test_list_players_in_tournament(session: Session, client: TestClient):
    event = create_event_in_db(session)
    tournament = create_tournament_in_db(session, event=event)
    player_a = create_player_in_db(session, nickname="PlayerA")
    player_b = create_player_in_db(session, nickname="PlayerB")
    tournament.add_player(player_a)
    tournament.add_player(player_b)
    session.add(tournament)
    session.commit()

    response = client.get(f"/tournaments/{tournament.id}/players")
    data = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert len(data) == 2
    nicknames = [link["player"]["nickname"] for link in data]
    assert "PlayerA" in nicknames
    assert "PlayerB" in nicknames


def test_list_players_in_tournament_empty(session: Session, client: TestClient):
    event = create_event_in_db(session)
    tournament = create_tournament_in_db(session, event=event)

    response = client.get(f"/tournaments/{tournament.id}/players")

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == []


def test_list_players_in_tournament_not_found(client: TestClient):
    response = client.get("/tournaments/00000000-0000-0000-0000-000000000000/players")

    assert response.status_code == status.HTTP_404_NOT_FOUND


# ---------------------------------------------------------------------------
# DELETE /tournaments/{tournament_id}/players/{player_id}
# ---------------------------------------------------------------------------


def test_remove_player_from_tournament(session: Session, client: TestClient):
    organizer = create_user_in_db(
        session, email="organizer@example.com", password="mypassword123"
    )
    event = create_event_in_db(session, organizer=organizer)
    tournament = create_tournament_in_db(session, event=event)
    player_a = create_player_in_db(session, nickname="PlayerA")
    player_b = create_player_in_db(session, nickname="PlayerB")
    tournament.add_player(player_a)
    tournament.add_player(player_b)
    session.add(tournament)
    session.commit()
    headers = get_auth_headers(client, "organizer@example.com", "mypassword123")

    response = client.delete(
        f"/tournaments/{tournament.id}/players/{player_a.id}",
        headers=headers,
    )
    data = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert len(data) == 1
    assert data[0]["player"]["nickname"] == "PlayerB"
    assert data[0]["has_paid_entry"] is False


def test_remove_player_from_tournament_when_player_not_in_tournament(
    session: Session, client: TestClient
):
    organizer = create_user_in_db(
        session, email="organizer@example.com", password="mypassword123"
    )
    event = create_event_in_db(session, organizer=organizer)
    tournament = create_tournament_in_db(session, event=event)
    player = create_player_in_db(session, nickname="PlayerA")
    headers = get_auth_headers(client, "organizer@example.com", "mypassword123")

    response = client.delete(
        f"/tournaments/{tournament.id}/players/{player.id}",
        headers=headers,
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_remove_player_from_tournament_tournament_not_found(
    session: Session, client: TestClient
):
    create_user_in_db(session, email="user@example.com", password="mypassword123")
    player = create_player_in_db(session, nickname="PlayerA")
    headers = get_auth_headers(client, "user@example.com", "mypassword123")

    response = client.delete(
        f"/tournaments/00000000-0000-0000-0000-000000000000/players/{player.id}",
        headers=headers,
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_remove_player_from_tournament_unauthorized(
    session: Session, client: TestClient
):
    create_user_in_db(session, email="attacker@example.com", password="mypassword123")
    event = create_event_in_db(session)
    tournament = create_tournament_in_db(session, event=event)
    player = create_player_in_db(session, nickname="PlayerA")
    headers = get_auth_headers(client, "attacker@example.com", "mypassword123")

    response = client.delete(
        f"/tournaments/{tournament.id}/players/{player.id}",
        headers=headers,
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_remove_player_from_tournament_player_not_found(
    session: Session, client: TestClient
):
    organizer = create_user_in_db(
        session, email="organizer@example.com", password="mypassword123"
    )
    event = create_event_in_db(session, organizer=organizer)
    tournament = create_tournament_in_db(session, event=event)
    headers = get_auth_headers(client, "organizer@example.com", "mypassword123")

    response = client.delete(
        f"/tournaments/{tournament.id}/players/00000000-0000-0000-0000-000000000000",
        headers=headers,
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_remove_player_from_tournament_unauthenticated(
    session: Session, client: TestClient
):
    event = create_event_in_db(session)
    tournament = create_tournament_in_db(session, event=event)
    player = create_player_in_db(session, nickname="PlayerA")

    response = client.delete(f"/tournaments/{tournament.id}/players/{player.id}")

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


# ---------------------------------------------------------------------------
# PUT /tournaments/{tournament_id}/players/{player_id}
# ---------------------------------------------------------------------------


def test_update_player_in_tournament(session: Session, client: TestClient):
    organizer = create_user_in_db(
        session, email="organizer@example.com", password="mypassword123"
    )
    event = create_event_in_db(session, organizer=organizer)
    tournament = create_tournament_in_db(session, event=event)
    player = create_player_in_db(session, nickname="PlayerA")
    tournament.add_player(player)
    session.add(tournament)
    session.commit()
    headers = get_auth_headers(client, "organizer@example.com", "mypassword123")

    response = client.patch(
        f"/tournaments/{tournament.id}/players/{player.id}",
        json={"has_paid_entry": True},
        headers=headers,
    )
    data = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert data["player"]["nickname"] == "PlayerA"
    assert data["has_paid_entry"] is True


def test_update_player_in_tournament_not_found(session: Session, client: TestClient):
    organizer = create_user_in_db(
        session, email="organizer@example.com", password="mypassword123"
    )
    event = create_event_in_db(session, organizer=organizer)
    tournament = create_tournament_in_db(session, event=event)
    headers = get_auth_headers(client, "organizer@example.com", "mypassword123")

    response = client.patch(
        f"/tournaments/{tournament.id}/players/00000000-0000-0000-0000-000000000000",
        json={"has_paid_entry": True},
        headers=headers,
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND


# ---------------------------------------------------------------------------
# GET /tournaments/{tournament_id}/rounds
# ---------------------------------------------------------------------------


def test_list_rounds_in_tournament(session: Session, client: TestClient):
    event = create_event_in_db(session)
    tournament = create_tournament_in_db(session, event=event)
    create_round_in_db(session, tournament=tournament, name="Round A")
    create_round_in_db(session, tournament=tournament, name="Round B")
    create_round_in_db(session, tournament=tournament, name="Round C")

    response = client.get(f"/tournaments/{tournament.id}/rounds")

    assert response.status_code == status.HTTP_200_OK
    assert len(response.json()) == 3
    assert response.json()[0]["name"] == "Round A"
    assert response.json()[1]["name"] == "Round B"
    assert response.json()[2]["name"] == "Round C"


def test_list_rounds_in_tournament_correct_order(session: Session, client: TestClient):
    event = create_event_in_db(session)
    tournament = create_tournament_in_db(session, event=event)
    round_a = create_round_in_db(session, tournament=tournament, name="Round A")
    round_b = create_round_in_db(session, tournament=tournament, name="Round B")
    round_c = create_round_in_db(session, tournament=tournament, name="Round C")

    round_a.order_index = 1
    round_b.order_index = 2
    round_c.order_index = 0
    session.commit()

    response = client.get(f"/tournaments/{tournament.id}/rounds")

    assert response.status_code == status.HTTP_200_OK
    assert len(response.json()) == 3
    assert response.json()[0]["name"] == "Round C"
    assert response.json()[1]["name"] == "Round A"
    assert response.json()[2]["name"] == "Round B"


# ---------------------------------------------------------------------------
# PUT /tournaments/{tournament_id}/rounds/order
# ---------------------------------------------------------------------------


def test_change_round_order(session: Session, client: TestClient):
    organizer = create_user_in_db(
        session, email="organizer@example.com", password="mypassword123"
    )
    event = create_event_in_db(session, organizer=organizer)
    tournament = create_tournament_in_db(session, event=event)
    round_a = create_round_in_db(session, tournament=tournament, name="Round A")
    round_b = create_round_in_db(session, tournament=tournament, name="Round B")
    round_c = create_round_in_db(session, tournament=tournament, name="Round C")
    headers = get_auth_headers(client, "organizer@example.com", "mypassword123")

    response = client.put(
        f"/tournaments/{tournament.id}/rounds/order",
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
    tournament = create_tournament_in_db(session, event=event)
    round_a = create_round_in_db(session, tournament=tournament, name="Round A")
    round_b = create_round_in_db(session, tournament=tournament, name="Round B")
    headers = get_auth_headers(client, "admin@example.com", "mypassword123")

    response = client.put(
        f"/tournaments/{tournament.id}/rounds/order",
        json=[str(round_b.id), str(round_a.id)],
        headers=headers,
    )

    session.refresh(round_a)
    session.refresh(round_b)

    assert response.status_code == status.HTTP_200_OK
    assert round_a.order_index == 1
    assert round_b.order_index == 0


def test_change_round_order_tournament_not_found(session: Session, client: TestClient):
    create_user_in_db(session, email="user@example.com", password="mypassword123")
    headers = get_auth_headers(client, "user@example.com", "mypassword123")

    response = client.put(
        "/tournaments/00000000-0000-0000-0000-000000000000/rounds/order",
        json=["00000000-0000-0000-0000-000000000000"],
        headers=headers,
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_change_round_order_unauthorized(session: Session, client: TestClient):
    create_user_in_db(session, email="attacker@example.com", password="mypassword123")
    event = create_event_in_db(session)
    tournament = create_tournament_in_db(session, event=event)
    round_a = create_round_in_db(session, tournament=tournament)
    headers = get_auth_headers(client, "attacker@example.com", "mypassword123")

    response = client.put(
        f"/tournaments/{tournament.id}/rounds/order",
        json=[str(round_a.id)],
        headers=headers,
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_change_round_order_unauthenticated(session: Session, client: TestClient):
    event = create_event_in_db(session)
    tournament = create_tournament_in_db(session, event=event)
    round_a = create_round_in_db(session, tournament=tournament)

    response = client.put(
        f"/tournaments/{tournament.id}/rounds/order",
        json=[str(round_a.id)],
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_change_round_order_round_count_mismatch(session: Session, client: TestClient):
    organizer = create_user_in_db(
        session, email="organizer@example.com", password="mypassword123"
    )
    event = create_event_in_db(session, organizer=organizer)
    tournament = create_tournament_in_db(session, event=event)
    round_a = create_round_in_db(session, tournament=tournament)
    create_round_in_db(session, tournament=tournament)
    headers = get_auth_headers(client, "organizer@example.com", "mypassword123")

    response = client.put(
        f"/tournaments/{tournament.id}/rounds/order",
        json=[str(round_a.id)],
        headers=headers,
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST


def test_change_round_order_round_mismatch(session: Session, client: TestClient):
    organizer = create_user_in_db(
        session, email="organizer@example.com", password="mypassword123"
    )
    event = create_event_in_db(session, organizer=organizer)
    tournament = create_tournament_in_db(session, event=event)
    round_a = create_round_in_db(session, tournament=tournament)
    create_round_in_db(session, tournament=tournament)
    headers = get_auth_headers(client, "organizer@example.com", "mypassword123")

    response = client.put(
        f"/tournaments/{tournament.id}/rounds/order",
        json=[str(round_a.id), "00000000-0000-0000-0000-000000000000"],
        headers=headers,
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST


def test_change_round_order_round_repeated_round(session: Session, client: TestClient):
    organizer = create_user_in_db(
        session, email="organizer@example.com", password="mypassword123"
    )
    event = create_event_in_db(session, organizer=organizer)
    tournament = create_tournament_in_db(session, event=event)
    round_a = create_round_in_db(session, tournament=tournament)
    create_round_in_db(session, tournament=tournament)
    headers = get_auth_headers(client, "organizer@example.com", "mypassword123")

    response = client.put(
        f"/tournaments/{tournament.id}/rounds/order",
        json=[str(round_a.id), str(round_a.id)],
        headers=headers,
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST


def test_change_round_order_round_already_started(session: Session, client: TestClient):
    organizer = create_user_in_db(
        session, email="organizer@example.com", password="mypassword123"
    )
    event = create_event_in_db(session, organizer=organizer)
    tournament = create_tournament_in_db(session, event=event)

    round_a = create_round_in_db(session, tournament=tournament)
    round_b = create_round_in_db(session, tournament=tournament)

    round_a.state = RoundState.IN_PROGRESS
    session.commit()

    headers = get_auth_headers(client, "organizer@example.com", "mypassword123")

    response = client.put(
        f"/tournaments/{tournament.id}/rounds/order",
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
    tournament = create_tournament_in_db(session, event=event)

    round_a = create_round_in_db(session, tournament=tournament)
    round_b = create_round_in_db(session, tournament=tournament)
    round_c = create_round_in_db(session, tournament=tournament)

    round_a.state = RoundState.IN_PROGRESS
    session.commit()

    headers = get_auth_headers(client, "organizer@example.com", "mypassword123")

    response = client.put(
        f"/tournaments/{tournament.id}/rounds/order",
        json=[str(round_a.id), str(round_c.id), str(round_b.id)],
        headers=headers,
    )

    assert response.status_code == status.HTTP_200_OK
    assert [r["id"] for r in response.json()] == [
        str(round_a.id),
        str(round_c.id),
        str(round_b.id),
    ]
