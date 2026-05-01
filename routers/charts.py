import uuid

from fastapi import APIRouter, HTTPException
from sqlmodel import select

from database import SessionDep
from models.chart import Chart, ChartCreate, ChartPublic, ChartUpdate

router = APIRouter(prefix="/charts", tags=["charts"])


@router.get("/", response_model=list[ChartPublic])
async def list_charts(session: SessionDep):
    """List all charts"""
    charts = session.exec(select(Chart)).all()
    return charts


@router.get("/{chart_id}", response_model=ChartPublic)
async def get_chart(chart_id: uuid.UUID, session: SessionDep):
    """Get a specific chart"""
    chart = session.get(Chart, chart_id)
    if not chart:
        raise HTTPException(status_code=404, detail="Chart not found")
    return chart


@router.post("/", response_model=ChartPublic)
async def create_chart(chart: ChartCreate, session: SessionDep):
    """Create a new chart"""
    db_chart = Chart.model_validate(chart)
    session.add(db_chart)
    session.commit()
    session.refresh(db_chart)
    return db_chart


@router.patch("/{chart_id}", response_model=ChartPublic)
async def update_chart(chart_id: uuid.UUID, chart: ChartUpdate, session: SessionDep):
    """Update a chart"""
    db_chart = session.get(Chart, chart_id)
    if not db_chart:
        raise HTTPException(status_code=404, detail="Chart not found")
    chart_data = chart.model_dump(exclude_unset=True)
    db_chart.sqlmodel_update(chart_data)
    session.add(db_chart)
    session.commit()
    session.refresh(db_chart)
    return db_chart


@router.delete("/{chart_id}")
async def delete_chart(chart_id: uuid.UUID, session: SessionDep):
    """Delete a chart"""
    db_chart = session.get(Chart, chart_id)
    if not db_chart:
        raise HTTPException(status_code=404, detail="Chart not found")
    session.delete(db_chart)
    session.commit()
    return {"detail": "Chart deleted"}
