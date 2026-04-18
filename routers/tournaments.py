import uuid
from datetime import date
from fastapi import APIRouter
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
async def get_tournament(tournament_id: int):
    """Get a specific tournament"""
    return {"tournament_id": tournament_id}


@router.post("/")
async def create_tournament(tournament: TournamentCreate, session: SessionDep):
    """Create a new tournament"""
    db_tournament = Tournament.model_validate(tournament)
    session.add(db_tournament)
    session.commit()
    session.refresh(db_tournament)
    return db_tournament


@router.put("/{tournament_id}")
async def update_tournament(tournament_id: int):
    """Update a tournament"""
    return {"tournament_id": tournament_id, "message": "Tournament updated"}


@router.delete("/{tournament_id}")
async def delete_tournament(tournament_id: int):
    """Delete a tournament"""
    return {"tournament_id": tournament_id, "message": "Tournament deleted"}
