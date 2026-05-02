import uuid

from fastapi import APIRouter, HTTPException
from sqlmodel import select

from database import SessionDep
from models.category import CategoryPublic
from models.player import Player, PlayerPublic
from models.tournament import (
    Tournament,
    TournamentCreate,
    TournamentPublic,
    TournamentUpdate,
)
from routers.users import UserDep

router = APIRouter(prefix="/tournaments", tags=["tournaments"])


@router.get("/", response_model=list[TournamentPublic])
async def list_tournaments(session: SessionDep):
    """List all tournaments"""
    tournaments = session.exec(select(Tournament)).all()
    return tournaments


@router.get("/{tournament_id}", response_model=TournamentPublic)
async def get_tournament(tournament_id: uuid.UUID, session: SessionDep):
    """Get a specific tournament"""
    db_tournament = session.get(Tournament, tournament_id)
    if not db_tournament:
        raise HTTPException(status_code=404, detail="Tournament not found")
    return db_tournament


@router.post("/", response_model=TournamentPublic)
async def create_tournament(
    tournament: TournamentCreate, session: SessionDep, user: UserDep
):
    """Create a new tournament"""
    db_tournament = Tournament.model_validate(tournament)
    session.add(db_tournament)
    session.commit()
    session.refresh(db_tournament)

    db_tournament.organizers.append(user)
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
    """Update a tournament"""
    db_tournament = session.get(Tournament, tournament_id)
    if not db_tournament:
        raise HTTPException(status_code=404, detail="Tournament not found")

    if not db_tournament.can_be_edited_by(user):
        raise HTTPException(
            status_code=403, detail="Not authorized to update this tournament"
        )

    tournament_data = tournament.model_dump(exclude_unset=True)
    db_tournament.sqlmodel_update(tournament_data)
    session.add(db_tournament)
    session.commit()
    session.refresh(db_tournament)
    return db_tournament


@router.delete("/{tournament_id}")
async def delete_tournament(
    tournament_id: uuid.UUID, session: SessionDep, user: UserDep
):
    """Delete a tournament"""
    db_tournament = session.get(Tournament, tournament_id)
    if not db_tournament:
        raise HTTPException(status_code=404, detail="Tournament not found")

    if not db_tournament.can_be_edited_by(user):
        raise HTTPException(
            status_code=403, detail="Not authorized to delete this tournament"
        )

    session.delete(db_tournament)
    session.commit()
    return {"detail": "Tournament deleted"}


@router.get("/{tournament_id}/categories", response_model=list[CategoryPublic])
async def list_tournament_categories(tournament_id: uuid.UUID, session: SessionDep):
    """List all categories for a tournament"""
    db_tournament = session.get(Tournament, tournament_id)
    if not db_tournament:
        raise HTTPException(status_code=404, detail="Tournament not found")
    return db_tournament.categories


@router.get("/{tournament_id}/organizers", response_model=list[PlayerPublic])
async def list_tournament_organizers(tournament_id: uuid.UUID, session: SessionDep):
    """Get all organizers for a tournament"""
    db_tournament = session.get(Tournament, tournament_id)

    if not db_tournament:
        raise HTTPException(status_code=404, detail="Tournament not found")

    return [user.player for user in db_tournament.organizers if user.player is not None]


@router.post(
    "/{tournament_id}/organizers/{player_id}", response_model=list[PlayerPublic]
)
async def add_organizer_to_tournament(
    tournament_id: uuid.UUID, player_id: uuid.UUID, session: SessionDep, user: UserDep
):
    """Add a player as an organizer to a tournament"""
    db_tournament = session.get(Tournament, tournament_id)
    if not db_tournament:
        raise HTTPException(status_code=404, detail="Tournament not found")

    if not db_tournament.can_be_edited_by(user):
        raise HTTPException(
            status_code=403, detail="Not authorized to add organizer to this tournament"
        )

    db_player = session.get(Player, player_id)
    if not db_player:
        raise HTTPException(status_code=404, detail="Player not found")

    if db_player.user is None:
        raise HTTPException(
            status_code=400, detail="Player is not registered with a user account"
        )

    if db_player.user in db_tournament.organizers:
        raise HTTPException(status_code=400, detail="Player is already an organizer")

    db_tournament.organizers.append(db_player.user)

    session.commit()

    return [user.player for user in db_tournament.organizers if user.player is not None]


@router.delete(
    "/{tournament_id}/organizers/{player_id}", response_model=list[PlayerPublic]
)
async def remove_organizer_from_tournament(
    tournament_id: uuid.UUID, player_id: uuid.UUID, session: SessionDep, user: UserDep
):
    """Remove a player as an organizer from a tournament"""
    db_tournament = session.get(Tournament, tournament_id)
    if not db_tournament:
        raise HTTPException(status_code=404, detail="Tournament not found")

    if not db_tournament.can_be_edited_by(user):
        raise HTTPException(
            status_code=403,
            detail="Not authorized to remove organizer from this tournament",
        )

    db_player = session.get(Player, player_id)
    if not db_player:
        raise HTTPException(status_code=404, detail="Player not found")

    if db_player.user is None:
        raise HTTPException(
            status_code=400, detail="Player is not registered with a user account"
        )

    if db_player.user not in db_tournament.organizers:
        raise HTTPException(status_code=400, detail="Player is not an organizer")

    if len(db_tournament.organizers) <= 1:
        raise HTTPException(
            status_code=400,
            detail="Cannot remove the last organizer from the tournament",
        )

    db_tournament.organizers.remove(db_player.user)

    session.commit()

    return [user.player for user in db_tournament.organizers if user.player is not None]
