import uuid
from fastapi import APIRouter, HTTPException
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
    scores = session.exec(select(Score)).all()
    return scores


@router.get("/{score_id}")
async def get_score(score_id: uuid.UUID, session: SessionDep):
    """Get a specific score"""
    score = session.get(Score, score_id)
    if not score:
        raise HTTPException(status_code=404, detail="Score not found")
    return score


@router.post("/")
async def create_score(score: ScoreCreate, session: SessionDep):
    """Create a new score"""
    db_round = session.get(Round, score.round_id)
    if not db_round:
        raise HTTPException(status_code=404, detail="Round not found")
    
    db_player = session.get(Player, score.player_id)
    if not db_player:
        raise HTTPException(status_code=404, detail="Player not found")
    
    db_chart = session.get(Chart, score.chart_id)
    if not db_chart:
        raise HTTPException(status_code=404, detail="Chart not found")
    
    if not any(link.player_id == score.player_id for link in db_round.player_links):
        raise HTTPException(status_code=400, detail="Player is not in the round")
    
    if not any(link.chart_id == score.chart_id for link in db_round.chart_links):
        raise HTTPException(status_code=400, detail="Chart is not in the round")

    db_score = Score.model_validate(score)
    session.add(db_score)
    session.commit()
    session.refresh(db_score)
    return db_score


@router.patch("/{score_id}")
async def update_score(score_id: uuid.UUID, score: ScoreUpdate, session: SessionDep):
    """Update a score"""
    return {"score_id": score_id, "message": "Score updated"}


@router.delete("/{score_id}")
async def delete_score(score_id: uuid.UUID, session: SessionDep):
    """Delete a score"""
    return {"score_id": score_id, "message": "Score deleted"}
