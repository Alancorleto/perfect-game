import uuid
from fastapi import APIRouter
from sqlmodel import Field, SQLModel, select, Relationship
from models.score import Score, ScoreCreate, ScoreUpdate
from models.round import Round
from models.player import Player
from models.chart import Chart
from database import SessionDep

router = APIRouter(
    prefix="/scores",
    tags=["scores"]
)


@router.get("/")
async def list_scores(session: SessionDep):
    """List all scores"""
    return {"message": "List of scores"}


@router.get("/{score_id}")
async def get_score(score_id: uuid.UUID, session: SessionDep):
    """Get a specific score"""
    return {"score_id": score_id}


@router.post("/")
async def create_score(score: ScoreCreate, session: SessionDep):
    """Create a new score"""
    return {"message": "Score created"}


@router.patch("/{score_id}")
async def update_score(score_id: uuid.UUID, score: ScoreUpdate, session: SessionDep):
    """Update a score"""
    return {"score_id": score_id, "message": "Score updated"}


@router.delete("/{score_id}")
async def delete_score(score_id: uuid.UUID, session: SessionDep):
    """Delete a score"""
    return {"score_id": score_id, "message": "Score deleted"}
