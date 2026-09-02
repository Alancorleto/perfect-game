import uuid
from typing import Annotated

from fastapi import APIRouter, File, HTTPException, Query, status
from sqlmodel import select

from database import SessionDep
from image_storage import upload_image
from models.chart import (
    Chart,
    ChartCreate,
    ChartPublic,
    ChartUpdate,
    ListChartsResponse,
)
from models.score import Score
from models.score_column import ScoreColumn
from routers.users import UserDep
from string_similarity import check_string_similarity

tag_metadata = {
    "name": "charts",
    "description": "A chart is what competitors play to compare scores against each other.",
    "externalDocs": {
        "description": "Learn more about charts here",
        "url": "https://github.com/Alancorleto/perfect-game/blob/main/entities-reference.md#charts",
    },
}

router = APIRouter(prefix="/charts", tags=["charts"])


@router.get("", response_model=ListChartsResponse)
async def list_charts(session: SessionDep, offset: int = 0, size: int = 20):
    """List all charts.\n
    Offset and size parameters are used for pagination."""
    charts = session.exec(select(Chart)).all()

    total_count = len(charts)
    if size > 0:
        charts = charts[offset : offset + size]

    return ListChartsResponse(
        charts=charts,
        offset=offset,
        size=len(charts),
        total_count=total_count,
    )


@router.get("/titles", response_model=list[str])
async def fuzzy_search_titles(
    session: SessionDep, search: str = Query(min_length=1)
) -> list[str]:
    """Receives a song name as input and returns a list of title URLs that are used by charts with a similar name.

    This endpoint helps organizers reuse title URLs for songs that have already been uploaded."""

    song_name = search

    charts = session.exec(select(Chart).where(Chart.title_url != None)).all()

    ranked_titles: list[tuple[float, str]] = []
    for chart in charts:
        names_are_similar = check_string_similarity(song_name, chart.song_name)
        if names_are_similar:
            ranked_titles.append((names_are_similar, chart.title_url))

    ranked_titles.sort(key=lambda item: item[0], reverse=True)
    return [title_url for _, title_url in ranked_titles]


@router.get("/{chart_id}", response_model=ChartPublic)
async def get_chart(chart_id: uuid.UUID, session: SessionDep):
    """Get a specific chart."""
    chart = session.get(Chart, chart_id)
    if not chart:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Chart not found"
        )
    return chart


@router.post("", response_model=ChartPublic)
async def create_chart(
    chart: ChartCreate,
    session: SessionDep,
    user: UserDep,
    score_column_id: uuid.UUID | None = None,
    score_id: uuid.UUID | None = None,
):
    """Create a new chart.

    To correctly use this endpoint, one of the following conditions must be met:
    - If the chart is for a score column, `score_column_id` must be provided
    - If the chart is for a score, `score_id` must be provided

    Any other combination will result in a `400 Bad Request` response.
    """
    db_chart = Chart.model_validate(chart)

    if score_column_id is not None and score_id is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="score_column_id and score_id cannot both be provided",
        )

    if score_column_id is not None:
        db_score_column = session.get(ScoreColumn, score_column_id)
        if db_score_column is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Score column not found"
            )

        if not db_score_column.can_be_edited_by(user):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Permission denied"
            )

        db_chart.score_column = db_score_column
    elif score_id is not None:
        db_score = session.get(Score, score_id)
        if db_score is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Score not found"
            )

        if not db_score.can_be_edited_by(user):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Permission denied"
            )

        db_chart.score = db_score

    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="score_column_id or score_id must be provided",
        )

    session.add(db_chart)
    session.commit()
    session.refresh(db_chart)

    return db_chart


@router.patch("/{chart_id}", response_model=ChartPublic)
async def update_chart(
    chart_id: uuid.UUID, chart: ChartUpdate, session: SessionDep, user: UserDep
):
    """Update a chart."""
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
    """Delete a chart."""
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
    """Upload a chart title."""
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
