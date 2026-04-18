import uuid
from datetime import date
from fastapi import APIRouter, HTTPException
from sqlmodel import Field, SQLModel, select

from database import SessionDep

router = APIRouter(
    prefix="/tournaments",
    tags=["tournaments"]
)


class TournamentBase(SQLModel):
    name: str
    location: str | None = None
    start_date: date | None = None


class Tournament(TournamentBase, table=True):
    id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        primary_key=True,
    )


class TournamentCreate(TournamentBase):
    pass


class TournamentPublic(TournamentBase):
    id: uuid.UUID


class TournamentUpdate(SQLModel):
    name: str | None = None
    location: str | None = None
    start_date: date | None = None


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
