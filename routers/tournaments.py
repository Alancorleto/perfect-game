import uuid
from models.tournament import Tournament, TournamentCreate, TournamentPublic, TournamentUpdate
from models.category import CategoryPublic
from datetime import date
from fastapi import APIRouter, HTTPException
from sqlmodel import Field, Relationship, SQLModel, select
from database import SessionDep

router = APIRouter(
    prefix="/tournaments",
    tags=["tournaments"]
)


@router.get("/")
async def list_tournaments(session: SessionDep):
    """List all tournaments"""
    tournaments = session.exec(select(Tournament)).all()
    return tournaments


@router.get("/{tournament_id}")
async def get_tournament(tournament_id: uuid.UUID, session: SessionDep):
    """Get a specific tournament"""
    db_tournament = session.get(Tournament, tournament_id)
    if not db_tournament:
        raise HTTPException(status_code=404, detail="Tournament not found")
    return db_tournament


@router.post("/")
async def create_tournament(tournament: TournamentCreate, session: SessionDep):
    """Create a new tournament"""
    db_tournament = Tournament.model_validate(tournament)
    session.add(db_tournament)
    session.commit()
    session.refresh(db_tournament)
    return db_tournament


@router.patch("/{tournament_id}")
async def update_tournament(tournament_id: uuid.UUID, tournament: TournamentUpdate, session: SessionDep):
    """Update a tournament"""
    db_tournament = session.get(Tournament, tournament_id)
    if not db_tournament:
        raise HTTPException(status_code=404, detail="Tournament not found")
    tournament_data = tournament.model_dump(exclude_unset=True)
    db_tournament.sqlmodel_update(tournament_data)
    session.add(db_tournament)
    session.commit()
    session.refresh(db_tournament)
    return db_tournament


@router.delete("/{tournament_id}")
async def delete_tournament(tournament_id: uuid.UUID, session: SessionDep):
    """Delete a tournament"""
    db_tournament = session.get(Tournament, tournament_id)
    if not db_tournament:
        raise HTTPException(status_code=404, detail="Tournament not found")
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
