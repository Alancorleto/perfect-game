import uuid

from fastapi import APIRouter, HTTPException, status
from sqlmodel import select

from database import SessionDep
from models.player import Player
from models.score import Score, ScoreCreate, ScorePublic, ScoreUpdate
from models.score_column import ScoreColumn
from routers.users import UserDep

description = """
Score is the entity that represents a **player**'s performance for a **score column**.
"""

tag_metadata = {
    "name": "scores",
    "description": description,
}

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

    db_score_column = session.get(ScoreColumn, score.score_column_id)
    if not db_score_column:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Score column not found"
        )

    if not db_score_column.can_be_edited_by(user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not an organizer for this tournament",
        )

    if not any(
        link.player_id == score.player_id
        for link in db_score_column.score_table.player_rows
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Player is not in the score table",
        )

    if any(
        score.player_id == score_column_score.player_id
        for score_column_score in db_score_column.scores
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A score already exists for this player and score column",
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
