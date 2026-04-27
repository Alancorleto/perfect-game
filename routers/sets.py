import uuid
from fastapi import APIRouter, HTTPException
from models.chart import Chart
from models.set_chart import SetChartLink
from sqlmodel import Field, SQLModel, select, Relationship
from models.set import Set, SetCreate
from models.round import Round
from database import SessionDep

router = APIRouter(
    prefix="/sets",
    tags=["sets"]
)


@router.post("/", response_model=Set)
def create_set(set: SetCreate, session: SessionDep):
    """Create a new set for a round."""
    round = session.get(Round, set.round_id)
    if not round:
        raise HTTPException(status_code=404, detail="Round not found")
    
    db_set = Set.model_validate(set)
    session.add(db_set)
    session.commit()
    session.refresh(db_set)
    return db_set


@router.get("/{set_id}", response_model=Set)
def get_set(set_id: uuid.UUID, session: SessionDep):
    """Get a specific set."""
    db_set = session.get(Set, set_id)
    if not db_set:
        raise HTTPException(status_code=404, detail="Set not found")
    return db_set


@router.post("/{set_id}/charts")
async def add_chart_to_set(set_id: uuid.UUID, chart_id: uuid.UUID, session: SessionDep):
    """Add a chart to a set"""
    db_set = session.get(Set, set_id)
    if not db_set:
        raise HTTPException(status_code=404, detail="Set not found")
    
    db_chart = session.get(Chart, chart_id)
    if not db_chart:
        raise HTTPException(status_code=404, detail="Chart not found")
    
    repeat_index = len([link for link in db_set.chart_links if link.chart_id == chart_id])
    
    order_index = len(db_set.chart_links)

    set_chart_link = SetChartLink(
        set=db_set,
        chart=db_chart,
        repeat_index=repeat_index,
        order_index=order_index,
    )
    
    db_set.chart_links.append(set_chart_link)
    
    session.add(set_chart_link)
    session.commit()
    session.refresh(set_chart_link)
    
    return set_chart_link
