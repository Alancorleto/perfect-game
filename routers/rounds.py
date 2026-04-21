import uuid
from fastapi import APIRouter, HTTPException
from sqlmodel import Field, SQLModel, select, Relationship
from models.round import Round, RoundCreate, RoundUpdate, RoundPublic
from database import SessionDep

router = APIRouter(
    prefix="/rounds",
    tags=["rounds"]
)


@router.get("/")
async def list_rounds(session: SessionDep):
    """List all rounds"""
    rounds = session.exec(select(Round)).all()
    return rounds


@router.get("/{round_id}")
async def get_round(round_id: uuid.UUID, session: SessionDep):
    """Get a specific round"""
    round = session.get(Round, round_id)
    if not round:
        raise HTTPException(status_code=404, detail="Round not found")
    return round


@router.post("/")
async def create_round(round: RoundCreate, session: SessionDep):
    """Create a new round"""
    db_round = Round.model_validate(round)
    session.add(db_round)
    session.commit()
    session.refresh(db_round)
    return db_round


@router.patch("/{round_id}")
async def update_round(round_id: uuid.UUID, round: RoundUpdate, session: SessionDep):
    """Update a round"""
    db_round = session.get(Round, round_id)
    if not db_round:
        raise HTTPException(status_code=404, detail="Round not found")
    round_data = round.model_dump(exclude_unset=True)
    db_round.sqlmodel_update(round_data)
    session.add(db_round)
    session.commit()
    session.refresh(db_round)
    return db_round


@router.delete("/{round_id}")
async def delete_round(round_id: uuid.UUID, session: SessionDep):
    """Delete a round"""
    db_round = session.get(Round, round_id)
    if not db_round:
        raise HTTPException(status_code=404, detail="Round not found")
    session.delete(db_round)
    session.commit()
    return {"detail": "Round deleted"}
