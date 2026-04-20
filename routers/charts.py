from models.chart import Chart, ChartCreate, ChartUpdate
from database import SessionDep
from fastapi import APIRouter
from sqlmodel import Field, SQLModel, select, Relationship


router = APIRouter(
    prefix="/charts",
    tags=["charts"]
)


@router.get("/")
async def list_charts(session: SessionDep):
    """List all charts"""
    charts = session.exec(select(Chart)).all()
    return charts


@router.get("/{chart_id}")
async def get_chart(chart_id: int):
    """Get a specific chart"""
    return {"chart_id": chart_id}


@router.post("/")
async def create_chart(chart: ChartCreate, session: SessionDep):
    """Create a new chart"""
    db_chart = Chart.model_validate(chart)
    session.add(db_chart)
    session.commit()
    session.refresh(db_chart)
    return db_chart


@router.put("/{chart_id}")
async def update_chart(chart_id: int):
    """Update a chart"""
    return {"chart_id": chart_id, "message": "Chart updated"}


@router.delete("/{chart_id}")
async def delete_chart(chart_id: int):
    """Delete a chart"""
    return {"chart_id": chart_id, "message": "Chart deleted"}
