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
    return {"message": "List of rounds"}


@router.get("/{round_id}")
async def get_round(round_id: uuid.UUID, session: SessionDep):
    """Get a specific round"""
    return {"round_id": round_id}


@router.post("/")
async def create_round(round: RoundCreate, session: SessionDep):
    """Create a new round"""
    db_round = Round.model_validate(round)
    session.add(db_round)
    session.commit()
    session.refresh(db_round)
    return db_round


@router.put("/{round_id}")
async def update_round(round_id: uuid.UUID, round: RoundUpdate, session: SessionDep):
    """Update a round"""
    return {"round_id": round_id, "message": "Round updated"}


@router.delete("/{round_id}")
async def delete_round(round_id: uuid.UUID, session: SessionDep):
    """Delete a round"""
    return {"round_id": round_id, "message": "Round deleted"}
