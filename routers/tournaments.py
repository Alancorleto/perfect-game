import datetime
import uuid

from fastapi import APIRouter, HTTPException, status
from sqlmodel import select

from database import SessionDep
from models.event import Event
from models.tournament import (
    Tournament,
    TournamentCreate,
    TournamentPublic,
    TournamentUpdate,
)
from models.tournament_invitation import (
    RequestStatus,
    TournamentInvitation,
    TournamentInvitationPublic,
    TournamentJoinRequest,
    TournamentJoinRequestPublic,
)
from models.tournament_player import (
    PlayerInTournament,
    TournamentPlayerLink,
    TournamentPlayerLinkUpdate,
)
from routers.players import Player, PlayerPublic
from routers.rounds import RoundPublic, RoundState
from routers.users import UserDep

description = """
# Tournaments
A tournament is a competition that happens within an **event**. When an event has more than one tournament, they are sometimes called "categories".\n
A tournament has one or more **rounds**. Each round has a specific order.\n
An organizer can add **guest players** to a tournament.\n
An organizer can **invite** a player with a registered account to a tournament, and the player can **accept** or **decline** the invitation.\n
A player can **request to join** a tournament, and an organizer can **accept** or **decline** the request.\n
An organizer can **track** wether a player has paid their entry fee.\n
"""

tag_metadata = {
    "name": "tournaments",
    "description": description,
}

router = APIRouter(prefix="/tournaments", tags=["tournaments"])


@router.get("/", response_model=list[TournamentPublic])
async def list_tournaments(session: SessionDep):
    """List all tournaments."""
    tournaments = session.exec(select(Tournament)).all()
    return tournaments


@router.get("/{tournament_id}", response_model=TournamentPublic)
async def get_tournament(tournament_id: uuid.UUID, session: SessionDep):
    """Get a specific tournament."""
    db_tournament = session.get(Tournament, tournament_id)
    if not db_tournament:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Tournament not found"
        )
    return db_tournament


@router.post("/", response_model=TournamentPublic)
async def create_tournament(
    tournament: TournamentCreate, session: SessionDep, user: UserDep
):
    """Create a new tournament."""

    event = session.get(Event, tournament.event_id)
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Event not found"
        )

    if not event.can_be_edited_by(user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not an organizer for this event",
        )

    db_tournament = Tournament.model_validate(tournament)

    session.add(db_tournament)
    session.commit()
    session.refresh(db_tournament)

    return db_tournament


@router.patch("/{tournament_id}", response_model=TournamentPublic)
async def update_tournament(
    tournament_id: uuid.UUID,
    tournament: TournamentUpdate,
    session: SessionDep,
    user: UserDep,
):
    """Update a tournament."""
    db_tournament = session.get(Tournament, tournament_id)
    if not db_tournament:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Tournament not found"
        )

    if not db_tournament.can_be_edited_by(user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not an organizer for this event",
        )

    tournament_data = tournament.model_dump(exclude_unset=True)
    db_tournament.sqlmodel_update(tournament_data)

    session.add(db_tournament)
    session.commit()
    session.refresh(db_tournament)

    return db_tournament


@router.delete("/{tournament_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_tournament(
    tournament_id: uuid.UUID, session: SessionDep, user: UserDep
):
    """Delete a tournament.

    A tournament can only be deleted if no rounds have started inside it."""
    db_tournament = session.get(Tournament, tournament_id)
    if not db_tournament:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Tournament not found"
        )

    if not db_tournament.can_be_deleted(user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permission denied",
        )

    session.delete(db_tournament)
    session.commit()


@router.post("/{tournament_id}/players/guest", response_model=list[PlayerPublic])
async def add_guest_player_to_tournament(
    tournament_id: uuid.UUID,
    player_id: uuid.UUID,
    session: SessionDep,
    user: UserDep,
):
    """Add a guest player to a tournament.

    The player must be a guest player previously created for the event."""
    db_tournament = session.get(Tournament, tournament_id)
    if not db_tournament:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Tournament not found"
        )

    if not db_tournament.can_be_edited_by(user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permission denied",
        )

    db_player = session.get(Player, player_id)
    if not db_player:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Player not found"
        )

    if db_player.user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Player is already registered",
        )

    if db_player in db_tournament.get_players_by_nickname():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Player is already in the tournament",
        )

    if db_player not in db_tournament.event.guest_players:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Player is not a guest player",
        )

    db_tournament.add_player(db_player)
    session.commit()
    session.refresh(db_tournament)

    return db_tournament.get_players_by_nickname()


@router.post("/{tournament_id}/players/bulk", response_model=list[PlayerPublic])
async def bulk_add_guest_players_to_tournament(
    tournament_id: uuid.UUID,
    player_ids: list[uuid.UUID],
    session: SessionDep,
    user: UserDep,
):
    """Bulk add guest players to a tournament.

    It filters players already in the tournament.

    The players must be guest players previously created for the event."""
    db_tournament = session.get(Tournament, tournament_id)
    if not db_tournament:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Tournament not found"
        )

    if not db_tournament.can_be_edited_by(user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not an organizer for this event",
        )

    player_ids_already_in_tournament = [
        p.id for p in db_tournament.get_players_by_nickname()
    ]
    player_ids = filter(
        lambda id: id not in player_ids_already_in_tournament, player_ids
    )

    for player_id in player_ids:
        db_player = session.get(Player, player_id)
        if not db_player:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Player with ID {player_id} not found",
            )

        if db_player.user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Player with ID {player_id} is already registered",
            )

        if db_player not in db_tournament.event.guest_players:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Player with ID {player_id} is not a guest player for this tournament",
            )

        db_tournament.add_player(db_player)

    session.add(db_tournament)
    session.commit()
    session.refresh(db_tournament)

    return db_tournament.get_players_by_nickname()


@router.get(
    "/{tournament_id}/invitations", response_model=list[TournamentInvitationPublic]
)
async def list_tournament_invitations(
    tournament_id: uuid.UUID, session: SessionDep, user: UserDep
):
    """List all invitations for a tournament."""
    db_tournament = session.get(Tournament, tournament_id)
    if not db_tournament:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Tournament not found"
        )

    if not db_tournament.can_be_edited_by(user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to view this tournament's invitations",
        )

    invitations: list[TournamentInvitationPublic] = []
    for invitation in db_tournament.invitations:
        if invitation.issued_at < datetime.datetime.now() - datetime.timedelta(days=1):
            continue

        invitations.append(
            TournamentInvitationPublic(
                tournament_id=invitation.tournament_id,
                player=invitation.player,
                status=invitation.status,
            )
        )

    return invitations


@router.post(
    "/{tournament_id}/invitations/{player_id}/", status_code=status.HTTP_204_NO_CONTENT
)
async def invite_player_to_tournament(
    tournament_id: uuid.UUID, player_id: uuid.UUID, session: SessionDep, user: UserDep
):
    """As an organizer, invite a player to a tournament."""
    db_tournament = session.get(Tournament, tournament_id)
    if not db_tournament:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Tournament not found"
        )

    if not db_tournament.can_be_edited_by(user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to edit this tournament",
        )

    db_player = session.get(Player, player_id)
    if not db_player:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Player not found"
        )

    if not db_player.user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Player is not registered",
        )

    if db_player in db_tournament.get_players_by_nickname():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Player is already in the tournament",
        )

    if db_player.user == user:
        db_tournament.add_player(db_player)
        session.commit()
        return

    db_invitation = next(
        (
            invitation
            for invitation in db_tournament.invitations
            if invitation.player_id == player_id
        ),
        TournamentInvitation(tournament_id=tournament_id, player_id=player_id),
    )

    db_invitation.status = RequestStatus.PENDING
    session.add(db_invitation)

    session.commit()


@router.post("/{tournament_id}/invitations/accept")
async def accept_tournament_invitation(
    tournament_id: uuid.UUID, session: SessionDep, user: UserDep
):
    """As a player, accept a tournament invitation."""

    player = user.player
    if not player:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User has no player associated",
        )

    db_tournament = session.get(Tournament, tournament_id)
    if not db_tournament:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Tournament not found"
        )

    db_invitation = session.get(TournamentInvitation, (tournament_id, player.id))
    if not db_invitation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Invitation not found"
        )

    if db_invitation.status == RequestStatus.ACCEPTED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invitation already accepted",
        )

    db_invitation.status = RequestStatus.ACCEPTED

    db_tournament.add_player(player)
    session.commit()


@router.post("/{tournament_id}/invitations/decline")
async def decline_tournament_invitation(
    tournament_id: uuid.UUID, session: SessionDep, user: UserDep
):
    """As a player, decline a tournament invitation."""
    player = user.player
    if not player:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User has no player associated",
        )

    db_tournament = session.get(Tournament, tournament_id)
    if not db_tournament:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Tournament not found"
        )

    db_invitation = session.get(TournamentInvitation, (tournament_id, player.id))
    if not db_invitation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Invitation not found"
        )

    if db_invitation.status == RequestStatus.DECLINED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invitation already declined",
        )

    if db_invitation.status == RequestStatus.ACCEPTED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invitation already accepted",
        )

    db_invitation.status = RequestStatus.DECLINED

    session.commit()


@router.get(
    "/{tournament_id}/join_requests", response_model=list[TournamentJoinRequestPublic]
)
async def list_tournament_join_requests(
    tournament_id: uuid.UUID, session: SessionDep, user: UserDep
):
    """List all join requests for a tournament."""
    tournament = session.get(Tournament, tournament_id)
    if not tournament:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Tournament not found"
        )

    if not tournament.can_be_edited_by(user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to edit tournament",
        )

    join_requests: list[TournamentJoinRequestPublic] = []
    for request in tournament.join_requests:
        if request.issued_at < datetime.datetime.now() - datetime.timedelta(days=1):
            continue

        join_requests.append(
            TournamentJoinRequestPublic(
                player_id=request.player_id,
                tournament=request.tournament,
                status=request.status,
            )
        )

    return join_requests


@router.post("/{tournament_id}/join_requests", status_code=status.HTTP_204_NO_CONTENT)
async def request_join_tournament(
    tournament_id: uuid.UUID, session: SessionDep, user: UserDep
):
    """As a player, request to join a tournament."""
    player = user.player

    if not player:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User has no player associated",
        )

    db_tournament = session.get(Tournament, tournament_id)
    if not db_tournament:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Tournament not found"
        )

    if player in db_tournament.get_players_by_nickname():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Player already in tournament",
        )

    if db_tournament.auto_accept_join_requests:
        db_tournament.add_player(player)
        session.commit()
        return

    join_request = next(
        (
            request
            for request in db_tournament.join_requests
            if request.player == player
        ),
        TournamentJoinRequest(tournament_id=tournament_id, player_id=player.id),
    )

    join_request.status = RequestStatus.PENDING

    session.add(join_request)

    session.commit()


@router.post("/{tournament_id}/join_requests/{player_id}/accept")
async def accept_tournament_join_request(
    tournament_id: uuid.UUID, player_id: uuid.UUID, session: SessionDep, user: UserDep
):
    """As an organizer, accept a tournament join request."""
    db_tournament = session.get(Tournament, tournament_id)
    if not db_tournament:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Tournament not found"
        )

    if not db_tournament.can_be_edited_by(user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to edit this tournament",
        )

    player = session.get(Player, player_id)
    if not player:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Player not found"
        )

    if player in db_tournament.get_players_by_nickname():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Player is already in the tournament",
        )

    join_request = next(
        (
            request
            for request in db_tournament.join_requests
            if request.player_id == player_id
        ),
        None,
    )
    if not join_request:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Join request not found"
        )

    if join_request.status != RequestStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Join request is not pending",
        )

    join_request.status = RequestStatus.ACCEPTED

    db_tournament.add_player(player)

    session.commit()


@router.post("/{tournament_id}/join_requests/{player_id}/decline")
async def decline_tournament_join_request(
    tournament_id: uuid.UUID, player_id: uuid.UUID, session: SessionDep, user: UserDep
):
    """As an organizer, decline a tournament join request."""
    db_tournament = session.get(Tournament, tournament_id)
    if not db_tournament:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Tournament not found"
        )

    if not db_tournament.can_be_edited_by(user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to edit this tournament",
        )

    player = session.get(Player, player_id)
    if not player:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Player not found"
        )

    if player in db_tournament.get_players_by_nickname():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Player is already in the tournament",
        )

    join_request = next(
        (
            request
            for request in db_tournament.join_requests
            if request.player_id == player_id
        ),
        None,
    )
    if not join_request:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Join request not found"
        )

    if join_request.status != RequestStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Join request is not pending",
        )

    join_request.status = RequestStatus.DECLINED

    session.commit()


@router.get("/{tournament_id}/players", response_model=list[PlayerInTournament])
async def list_players_in_tournament(tournament_id: uuid.UUID, session: SessionDep):
    """List all players in a tournament."""
    db_tournament = session.get(Tournament, tournament_id)
    if not db_tournament:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Tournament not found"
        )
    return db_tournament.player_links


@router.patch(
    "/{tournament_id}/players/{player_id}",
    response_model=PlayerInTournament,
)
async def update_player_in_tournament(
    tournament_id: uuid.UUID,
    player_id: uuid.UUID,
    tournament_player_link: TournamentPlayerLinkUpdate,
    session: SessionDep,
    user: UserDep,
):
    """Update player information related to a tournament. For example, if a player paid for their entry."""
    db_tournament_player_link = session.get(
        TournamentPlayerLink, (tournament_id, player_id)
    )
    if not db_tournament_player_link:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tournament player link not found",
        )

    if not db_tournament_player_link.tournament.can_be_edited_by(user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Unauthorized to edit tournament",
        )

    tournament_player_link_data = tournament_player_link.model_dump(exclude_unset=True)
    db_tournament_player_link.sqlmodel_update(tournament_player_link_data)

    session.add(db_tournament_player_link)
    session.commit()
    session.refresh(db_tournament_player_link)

    return db_tournament_player_link


@router.delete(
    "/{tournament_id}/players/{player_id}", response_model=list[PlayerInTournament]
)
async def remove_player_from_tournament(
    tournament_id: uuid.UUID, player_id: uuid.UUID, session: SessionDep, user: UserDep
):
    """Remove a player from a tournament.

    A player can only be removed from a tournament if no rounds have started inside it."""
    db_tournament = session.get(Tournament, tournament_id)
    if not db_tournament:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Tournament not found"
        )

    if not db_tournament.can_be_edited_by(user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Unauthorized to edit tournament",
        )

    db_player = session.get(Player, player_id)
    if not db_player:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Player not found"
        )

    db_tournament_player_link = session.get(
        TournamentPlayerLink, (tournament_id, player_id)
    )
    if not db_tournament_player_link:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Player not found in tournament",
        )

    if any(round.state != RoundState.NOT_STARTED for round in db_tournament.rounds):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tournament has already started",
        )

    session.delete(db_tournament_player_link)
    session.commit()
    session.refresh(db_tournament)

    return db_tournament.player_links


@router.get("/{tournament_id}/rounds", response_model=list[RoundPublic])
async def list_rounds_in_tournament(
    tournament_id: uuid.UUID,
    session: SessionDep,
):
    """List all rounds in a tournament by order."""
    db_tournament = session.get(Tournament, tournament_id)
    if not db_tournament:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Tournament not found"
        )

    return db_tournament.get_rounds_by_order()


@router.put("/{tournament_id}/rounds/order", response_model=list[RoundPublic])
async def change_round_order_in_tournament(
    tournament_id: uuid.UUID,
    new_round_order: list[uuid.UUID],
    session: SessionDep,
    user: UserDep,
):
    """Change the order of rounds within a tournament.

    The provided list must be the IDs of the rounds in the tournament in their new order."""
    db_tournament = session.get(Tournament, tournament_id)
    if not db_tournament:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Tournament not found"
        )

    if not db_tournament.can_be_edited_by(user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not an organizer for this event",
        )

    existing_rounds = {round.id: round for round in db_tournament.rounds}

    if len(new_round_order) != len(existing_rounds):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Round order must match the number of rounds in the tournament",
        )

    if set(new_round_order) != set(existing_rounds.keys()):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Round order must have the same rounds as the tournament",
        )

    if any(
        round.state != RoundState.NOT_STARTED
        and new_round_order[round.order_index] != round_id
        for round_id, round in existing_rounds.items()
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot change round order for a round that has already started",
        )

    for new_index, round_id in enumerate(new_round_order):
        round = existing_rounds[round_id]
        if not round:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Round not found"
            )

        round.order_index = new_index
        session.add(round)

    session.commit()
    session.refresh(db_tournament)

    return db_tournament.get_rounds_by_order()
