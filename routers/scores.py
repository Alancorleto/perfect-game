import uuid

from fastapi import APIRouter, HTTPException, status
from sqlmodel import select

from database import SessionDep
from models.chart import Chart
from models.chart_slot import ChartSlot
from models.player import Player
from models.score import Score, ScoreCreate, ScorePublic, ScoreUpdate
from routers.users import UserDep

router = APIRouter(prefix="/scores", tags=["scores"])


@router.get("/", response_model=list[ScorePublic])
async def list_scores(session: SessionDep):
    """List all scores"""
    scores = session.exec(select(Score)).all()
    return scores


@router.get("/{score_id}", response_model=ScorePublic)
async def get_score(score_id: uuid.UUID, session: SessionDep):
    """Get a specific score"""
    score = session.get(Score, score_id)
    if not score:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Score not found"
        )
    return score


@router.post("/", response_model=ScorePublic)
async def create_score(score: ScoreCreate, session: SessionDep, user: UserDep):
    """Create a new score"""
    db_player = session.get(Player, score.player_id)
    if not db_player:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Player not found"
        )

    db_chart = session.get(Chart, score.chart_id)
    if not db_chart:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Chart not found"
        )

    db_chart_slot = session.get(ChartSlot, score.chart_slot_id)
    if not db_chart_slot:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Chart slot not found"
        )

    if not db_chart_slot.can_be_edited_by(user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not an organizer for this tournament",
        )

    if not any(
        link.player_id == score.player_id
        for link in db_chart_slot.score_table.player_rows
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Player is not in the set",
        )

    if db_chart not in db_chart_slot.score_table.charts:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Chart {db_chart} is not in the set",
        )

    if db_chart_slot.chart is not None and db_chart_slot.chart != db_chart:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Chart {db_chart} does not correspond with column {db_chart_slot.order_index}",
        )

    if any(
        score.player_id == chart_slot_score.player_id
        for chart_slot_score in db_chart_slot.scores
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A score already exists for this player and chart slot",
        )

    db_score = Score.model_validate(score)
    session.add(db_score)
    session.commit()
    session.refresh(db_score)
    return db_score


@router.patch("/{score_id}", response_model=ScorePublic)
async def update_score(
    score_id: uuid.UUID, score: ScoreUpdate, session: SessionDep, user: UserDep
):
    """Update a score"""
    db_score = session.get(Score, score_id)
    if not db_score:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Score not found"
        )

    if not db_score.can_be_edited_by(user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not allowed to edit this score",
        )

    score_data = score.model_dump(exclude_unset=True)

    db_score.sqlmodel_update(score_data)
    session.add(db_score)
    session.commit()
    session.refresh(db_score)

    return db_score


@router.delete("/{score_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_score(score_id: uuid.UUID, session: SessionDep, user: UserDep):
    """Delete a score"""
    db_score = session.get(Score, score_id)
    if not db_score:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Score not found"
        )

    if not db_score.can_be_deleted(user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permission denied",
        )

    session.delete(db_score)
    session.commit()
