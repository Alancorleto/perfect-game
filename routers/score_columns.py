import uuid

from fastapi import APIRouter, HTTPException, status
from sqlmodel import select

from database import SessionDep
from models.round import RoundState
from models.score_column import (
    ScoreColumn,
    ScoreColumnCreate,
    ScoreColumnPublic,
    ScoreColumnUpdate,
)
from models.score_table import ScoreTable
from routers.users import UserDep

description = """
# Score Columns
Score column is the entity that contains a list of scores that are meant
to be compared against each other.\n
A score column is always associated with a **score table** and has an **order_index**.\n
A score column can have an optional associated **chart** which represents
the chart that is meant to be played.\n
If a chart is not specified, the score column can have an associated **chart column**
which represents the chart that each individual player played.
"""

tag_metadata = {
    "name": "score_columns",
    "description": description,
}

router = APIRouter(prefix="/score_columns", tags=["score_columns"])


@router.get("/", response_model=list[ScoreColumnPublic])
async def list_score_columns(session: SessionDep):
    """List all score columns."""
    score_columns = session.exec(select(ScoreColumn)).all()
    return score_columns


@router.post("/", response_model=ScoreColumnPublic)
async def create_score_column(
    score_column: ScoreColumnCreate, session: SessionDep, user: UserDep
):
    """Create a score column for a score table."""
    db_score_table = session.get(ScoreTable, score_column.score_table_id)
    if not db_score_table:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Score table not found"
        )

    if not db_score_table.can_be_edited_by(user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not an organizer for this event",
        )

    db_score_column = ScoreColumn.model_validate(score_column)

    db_score_column.order_index = len(db_score_table.score_columns)

    session.add(db_score_column)
    session.commit()
    session.refresh(db_score_column)

    return db_score_column


@router.get("/{score_column_id}", response_model=ScoreColumnPublic)
async def get_score_column(
    score_column_id: uuid.UUID,
    session: SessionDep,
):
    """Get a score column."""
    db_score_column = session.get(ScoreColumn, score_column_id)
    if not db_score_column:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Score column not found"
        )
    return db_score_column


@router.patch("/{score_column_id}", response_model=ScoreColumnPublic)
async def update_score_column(
    score_column_id: uuid.UUID,
    score_column_update: ScoreColumnUpdate,
    session: SessionDep,
    user: UserDep,
):
    """Update a score column."""
    db_score_column = session.get(ScoreColumn, score_column_id)
    if not db_score_column:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Score column not found"
        )

    if not db_score_column.can_be_edited_by(user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not an organizer for this event",
        )

    score_column_data = score_column_update.model_dump(exclude_unset=True)
    db_score_column.sqlmodel_update(score_column_data)

    session.add(db_score_column)
    session.commit()
    session.refresh(db_score_column)

    return db_score_column


@router.delete("/{score_column_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_score_column(
    score_column_id: uuid.UUID, session: SessionDep, user: UserDep
):
    """Delete a score column.

    A score column cannot be deleted if the round is finished."""
    db_score_column = session.get(ScoreColumn, score_column_id)
    if not db_score_column:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Score column not found"
        )

    if not db_score_column.can_be_deleted(user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not allowed to delete this score column",
        )

    db_score_table = db_score_column.score_table
    if not db_score_table:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Score table not found"
        )

    if db_score_table.round.state == RoundState.FINISHED:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot delete score column after round is finished",
        )

    deleted_column_order_index = db_score_column.order_index

    session.delete(db_score_column)

    for column in db_score_table.score_columns:
        if column.order_index > deleted_column_order_index:
            column.order_index -= 1
            session.add(column)

    session.commit()
    session.refresh(db_score_table)
