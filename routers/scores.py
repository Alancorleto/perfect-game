import uuid

from fastapi import APIRouter, HTTPException
from sqlmodel import select

from database import SessionDep
from models.chart import Chart
from models.player import Player
from models.score import Score, ScoreCreate, ScorePublic, ScoreUpdate
from models.score_entry import ScoreEntry
from models.set import Set
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
        raise HTTPException(status_code=404, detail="Score not found")
    return score


@router.post("/")
async def create_score(score: ScoreCreate, session: SessionDep, user: UserDep):
    """Create a new score"""
    db_player = session.get(Player, score.player_id)
    if not db_player:
        raise HTTPException(status_code=404, detail="Player not found")

    db_chart = session.get(Chart, score.chart_id)
    if not db_chart:
        raise HTTPException(status_code=404, detail="Chart not found")

    db_score = Score.model_validate(score)
    session.add(db_score)

    # Add the score to an existing set if set_id and order_index are provided.
    if score.set_id is not None and score.order_index is not None:
        db_set = session.get(Set, score.set_id)
        if not db_set:
            raise HTTPException(status_code=404, detail="Set not found")

        if not db_set.can_be_edited_by(user):
            raise HTTPException(
                status_code=403, detail="You are not an organizer for this tournament"
            )

        if not any(link.player_id == score.player_id for link in db_set.player_links):
            raise HTTPException(status_code=400, detail="Player is not in the set")

        if not any(
            chart_slot.chart_id == score.chart_id
            and chart_slot.order_index == score.order_index
            for chart_slot in db_set.chart_slots
        ):
            raise HTTPException(
                status_code=400,
                detail=f"Chart with index {score.order_index} is not in the set",
            )

        chart_slot = next(
            chart_slot
            for chart_slot in db_set.chart_slots
            if chart_slot.order_index == score.order_index
        )

        if any(
            score_entry.score.player_id == score.player_id
            for score_entry in chart_slot.score_entries
        ):
            raise HTTPException(
                status_code=400,
                detail="A score already exists for this player, set, and order index",
            )

        score_link: ScoreEntry = ScoreEntry(score=db_score, chart_slot=chart_slot)

        session.add(score_link)

    session.commit()
    session.refresh(db_score)
    return db_score


@router.patch("/{score_id}")
async def update_score(
    score_id: uuid.UUID, score: ScoreUpdate, session: SessionDep, user: UserDep
):
    """Update a score"""
    db_score = session.get(Score, score_id)
    if not db_score:
        raise HTTPException(status_code=404, detail="Score not found")

    if not db_score.can_be_edited_by(user):
        raise HTTPException(
            status_code=403, detail="You are not allowed to edit this score"
        )

    score_data = score.model_dump(exclude_unset=True)
    db_score.sqlmodel_update(score_data)
    session.add(db_score)
    session.commit()
    session.refresh(db_score)
    return db_score


@router.delete("/{score_id}")
async def delete_score(score_id: uuid.UUID, session: SessionDep, user: UserDep):
    """Delete a score"""
    db_score = session.get(Score, score_id)
    if not db_score:
        raise HTTPException(status_code=404, detail="Score not found")

    if not db_score.can_be_edited_by(user):
        raise HTTPException(
            status_code=403, detail="You are not allowed to delete this score"
        )

    session.delete(db_score)
    session.commit()
    return {"detail": "Score deleted"}
