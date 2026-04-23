import uuid
from fastapi import APIRouter, HTTPException
from sqlmodel import Field, SQLModel, select, Relationship
from models.sum_format import SumFormat, SumFormatCreate
from models.round import Round
from database import SessionDep

router = APIRouter(
    prefix="/formats/sum",
    tags=["sum_formats"]
)


@router.post("/", response_model=SumFormat)
def create_sum_format(sum_format: SumFormatCreate, session: SessionDep):
    """Create a new sum format for a round."""
    round = session.get(Round, sum_format.round_id)
    if not round:
        raise HTTPException(status_code=404, detail="Round not found")
    if round.sum_format:
        raise HTTPException(status_code=400, detail="Round already has a sum format")
    
    db_format = SumFormat.model_validate(sum_format)
    session.add(db_format)
    session.commit()
    session.refresh(db_format)
    return db_format


@router.get("/{round_id}", response_model=SumFormat)
def get_sum_format(round_id: uuid.UUID, session: SessionDep):
    """Get the sum format for a specific round."""
    round = session.get(Round, round_id)
    if not round:
        raise HTTPException(status_code=404, detail="Round not found")
    if not round.sum_format:
        raise HTTPException(status_code=404, detail="Sum format not found for this round")
    return round.sum_format
