import uuid

from fastapi import APIRouter, HTTPException, status
from sqlmodel import select

from database import SessionDep
from models.chart import Chart
from models.chart_slot import (
    ChartSlot,
    ChartSlotCreate,
    ChartSlotPublic,
    ChartSlotUpdate,
)
from models.score_table import ScoreTable
from routers.users import UserDep

router = APIRouter(prefix="/chart_slots", tags=["chart_slots"])


@router.get("/", response_model=list[ChartSlotPublic])
async def list_chart_slots(session: SessionDep, user: UserDep):
    """List all chart slots."""
    chart_slots = session.exec(select(ChartSlot)).all()
    return chart_slots


@router.post("/", response_model=ChartSlotPublic)
async def create_chart_slot(
    chart_slot: ChartSlotCreate, session: SessionDep, user: UserDep
):
    """Create a chart slot."""
    db_set = session.get(ScoreTable, chart_slot.score_table_id)
    if not db_set:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Set not found"
        )

    if not db_set.can_be_edited_by(user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not an organizer for this tournament",
        )

    if chart_slot.chart_id is not None:
        db_chart = session.get(Chart, chart_slot.chart_id)
        if not db_chart:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Chart not found"
            )

    db_chart_slot = ChartSlot.model_validate(chart_slot)

    db_chart_slot.order_index = len(db_set.chart_slots)

    session.add(db_chart_slot)
    session.commit()
    session.refresh(db_chart_slot)

    return db_chart_slot


@router.get("/{chart_slot_id}", response_model=ChartSlotPublic)
async def get_chart_slot(
    chart_slot_id: uuid.UUID,
    session: SessionDep,
):
    """Get a chart slot."""
    db_chart_slot = session.get(ChartSlot, chart_slot_id)
    if not db_chart_slot:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Chart slot not found"
        )
    return db_chart_slot


@router.patch("/{chart_slot_id}", response_model=ChartSlotPublic)
async def update_chart_slot(
    chart_slot_id: uuid.UUID,
    chart_slot_update: ChartSlotUpdate,
    session: SessionDep,
    user: UserDep,
):
    """Update a chart slot."""
    db_chart_slot = session.get(ChartSlot, chart_slot_id)
    if not db_chart_slot:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Chart slot not found"
        )

    if not db_chart_slot.can_be_edited_by(user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not an organizer for this tournament",
        )

    if chart_slot_update.chart_id:
        db_chart = session.get(Chart, chart_slot_update.chart_id)
        if not db_chart:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Chart not found"
            )

        if db_chart not in db_chart_slot.score_table.charts:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Chart not in score table",
            )

    chart_slot_data = chart_slot_update.model_dump(exclude_unset=True)
    db_chart_slot.sqlmodel_update(chart_slot_data)

    session.add(db_chart_slot)
    session.commit()
    session.refresh(db_chart_slot)

    return db_chart_slot


@router.delete("/{chart_slot_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_chart_slot(
    chart_slot_id: uuid.UUID, session: SessionDep, user: UserDep
):
    """Delete a chart slot."""
    db_chart_slot = session.get(ChartSlot, chart_slot_id)
    if not db_chart_slot:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Chart slot not found"
        )

    if not db_chart_slot.can_be_deleted(user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not allowed to delete this chart slot",
        )

    db_set = db_chart_slot.score_table
    if not db_set:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Set not found"
        )

    deleted_slot_order_index = db_chart_slot.order_index

    session.delete(db_chart_slot)

    for slot in db_set.chart_slots:
        if slot.order_index > deleted_slot_order_index:
            slot.order_index -= 1
            session.add(slot)

    session.commit()
    session.refresh(db_set)
