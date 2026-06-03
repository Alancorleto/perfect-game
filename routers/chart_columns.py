import uuid

from fastapi import APIRouter, HTTPException, status
from sqlmodel import select

from database import SessionDep
from models.chart_column import (
    ChartColumn,
    ChartColumnCreate,
    ChartColumnPublic,
    ChartColumnUpdate,
)
from models.score_column import ScoreColumn
from routers.users import UserDep

description = """
# Chart Columns
A chart column is used when a **score column** has no **chart** associated with it,
for example, when each player played a chart of their own choice.\n
A chart column represents **which chart** each player played for the associated score column.
"""

tag_metadata = {
    "name": "chart_columns",
    "description": description,
}

router = APIRouter(prefix="/chart_columns", tags=["chart_columns"])


@router.get("/", response_model=list[ChartColumnPublic])
async def list_chart_columns(session: SessionDep):
    """List all chart columns."""
    chart_columns = session.exec(select(ChartColumn)).all()
    return chart_columns


@router.post("/", response_model=ChartColumnPublic)
async def create_chart_column(
    chart_column: ChartColumnCreate, session: SessionDep, user: UserDep
):
    """Create a chart column for a score column."""
    db_score_column = session.get(ScoreColumn, chart_column.score_column_id)
    if not db_score_column:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Score column not found"
        )

    if not db_score_column.can_be_edited_by(user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not an organizer for this event",
        )

    if db_score_column.chart_column is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Score column already has a chart column",
        )

    db_chart_column = ChartColumn.model_validate(chart_column)

    session.add(db_chart_column)
    session.commit()
    session.refresh(db_chart_column)

    return db_chart_column


@router.get("/{chart_column_id}", response_model=ChartColumnPublic)
async def get_chart_column(
    chart_column_id: uuid.UUID,
    session: SessionDep,
):
    """Get a chart column."""
    db_chart_column = session.get(ChartColumn, chart_column_id)
    if not db_chart_column:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Chart column not found"
        )
    return db_chart_column


@router.patch("/{chart_column_id}", response_model=ChartColumnPublic)
async def update_chart_column(
    chart_column_id: uuid.UUID,
    chart_column_update: ChartColumnUpdate,
    session: SessionDep,
    user: UserDep,
):
    """Update a chart column."""
    db_chart_column = session.get(ChartColumn, chart_column_id)
    if not db_chart_column:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Chart column not found"
        )

    if not db_chart_column.can_be_edited_by(user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not an organizer for this event",
        )

    chart_column_data = chart_column_update.model_dump(exclude_unset=True)
    db_chart_column.sqlmodel_update(chart_column_data)

    session.add(db_chart_column)
    session.commit()
    session.refresh(db_chart_column)

    return db_chart_column


@router.delete("/{chart_column_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_chart_column(
    chart_column_id: uuid.UUID, session: SessionDep, user: UserDep
):
    """Delete a chart column."""
    db_chart_column = session.get(ChartColumn, chart_column_id)
    if not db_chart_column:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Chart column not found"
        )

    if not db_chart_column.can_be_deleted(user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not allowed to delete this chart column",
        )

    db_score_column = db_chart_column.score_column
    if not db_score_column:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Score column for this chart column not found",
        )

    session.delete(db_chart_column)

    session.commit()
    session.refresh(db_score_column)
