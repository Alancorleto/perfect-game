import uuid
from typing import Annotated

from fastapi import APIRouter, File, HTTPException, status
from sqlmodel import select

from database import SessionDep
from image_storage import upload_image
from models.chart import Chart, ChartCreate, ChartPublic, ChartUpdate
from routers.users import UserDep

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
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Chart not found"
        )
    return chart


@router.post("/", response_model=ChartPublic)
async def create_chart(chart: ChartCreate, session: SessionDep, user: UserDep):
    """Create a new chart"""

    chart_data = chart.model_dump()
    chart_data["creator_id"] = user.id
    db_chart = Chart.model_validate(chart_data)

    session.add(db_chart)
    session.commit()
    session.refresh(db_chart)

    return db_chart


@router.patch("/{chart_id}", response_model=ChartPublic)
async def update_chart(
    chart_id: uuid.UUID, chart: ChartUpdate, session: SessionDep, user: UserDep
):
    """Update a chart"""
    db_chart = session.get(Chart, chart_id)
    if not db_chart:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Chart not found"
        )

    if not db_chart.can_be_edited_by(user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permission denied",
        )

    chart_data = chart.model_dump(exclude_unset=True)
    db_chart.sqlmodel_update(chart_data)

    session.add(db_chart)
    session.commit()
    session.refresh(db_chart)

    return db_chart


@router.delete("/{chart_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_chart(chart_id: uuid.UUID, session: SessionDep, user: UserDep):
    """Delete a chart"""
    db_chart = session.get(Chart, chart_id)
    if not db_chart:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Chart not found"
        )

    if not db_chart.can_be_deleted(user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permission denied",
        )

    session.delete(db_chart)
    session.commit()


@router.post("/{chart_id}/title", response_model=ChartPublic)
async def upload_chart_title(
    chart_id: uuid.UUID, title_file: Annotated[bytes, File()], session: SessionDep
):
    """Upload a song title"""
    db_chart = session.get(Chart, chart_id)
    if not db_chart:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Chart not found"
        )

    file_name = f"{db_chart.id}.png"
    db_chart.title_url = await upload_image(title_file, file_name, "titles")

    session.add(db_chart)
    session.commit()
    session.refresh(db_chart)

    return db_chart
