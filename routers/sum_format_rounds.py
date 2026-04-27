import uuid
from fastapi import APIRouter, HTTPException
from models.chart import Chart
from models.sum_format_chart import SumFormatChartLink
from sqlmodel import Field, SQLModel, select, Relationship
from models.sum_format_round import SumFormatRound, SumFormatRoundCreate
from models.round import Round
from database import SessionDep

router = APIRouter(
    prefix="/formats/sum",
    tags=["sum_formats"]
)


@router.post("/", response_model=SumFormatRound)
def create_sum_format_round(sum_format: SumFormatRoundCreate, session: SessionDep):
    """Create a new sum format for a round."""
    round = session.get(Round, sum_format.round_id)
    if not round:
        raise HTTPException(status_code=404, detail="Round not found")
    if round.sum_format:
        raise HTTPException(status_code=400, detail="Round already has a sum format")
    
    db_format = SumFormatRound.model_validate(sum_format)
    session.add(db_format)
    session.commit()
    session.refresh(db_format)
    return db_format


@router.get("/{round_id}", response_model=SumFormatRound)
def get_sum_format_round(round_id: uuid.UUID, session: SessionDep):
    """Get the sum format for a specific round."""
    round = session.get(Round, round_id)
    if not round:
        raise HTTPException(status_code=404, detail="Round not found")
    if not round.sum_format:
        raise HTTPException(status_code=404, detail="Sum format not found for this round")
    return round.sum_format


@router.post("/charts")
async def add_chart_to_sum_format_round(round_id: uuid.UUID, chart_id: uuid.UUID, session: SessionDep):
    """Add a chart to a round"""
    db_round = session.get(Round, round_id)
    if not db_round:
        raise HTTPException(status_code=404, detail="Round not found")
    
    db_chart = session.get(Chart, chart_id)
    if not db_chart:
        raise HTTPException(status_code=404, detail="Chart not found")
    
    repeat_index = len([link for link in db_round.sum_format.chart_links if link.chart_id == chart_id])
    
    order_index = len(db_round.sum_format.chart_links)

    sum_format_chart_link = SumFormatChartLink(
        round=db_round,
        chart=db_chart,
        repeat_index=repeat_index,
        order_index=order_index,
    )
    
    db_round.sum_format.chart_links.append(sum_format_chart_link)
    
    session.add(sum_format_chart_link)
    session.commit()
    session.refresh(sum_format_chart_link)
    
    return sum_format_chart_link
