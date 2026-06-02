import re
import unicodedata
import uuid
from typing import Annotated

from fastapi import APIRouter, File, HTTPException, Query, status
from sqlmodel import select

from database import SessionDep
from image_storage import upload_image
from models.chart import Chart, ChartCreate, ChartPublic, ChartUpdate
from models.chart_column import ChartColumn
from models.chart_column_entry import ChartColumnEntry
from models.player import Player
from models.score_column import ScoreColumn
from routers.users import UserDep

description = """
A chart is a level in rhythm games terms.\n
A chart must be associated with any of the following:\n
- A **score column**, which represents the chart that must be played in that column\n
- A combination of **chart column** and **player**, which represents the chart that was played in that column by that player\n
A chart has a song name, a player count, a mode, a level difficulty, and a title image which can be uploaded by an organizer.
"""

tag_metadata = {
    "name": "charts",
    "description": description,
}

router = APIRouter(prefix="/charts", tags=["charts"])


@router.get("/", response_model=list[ChartPublic])
async def list_charts(session: SessionDep):
    """List all charts"""
    charts = session.exec(select(Chart)).all()
    return charts


@router.get("/titles", response_model=list[str])
async def fuzzy_search_titles(
    session: SessionDep, search: str = Query(min_length=1)
) -> list[str]:
    """Return chart title URLs that approximately match a song name."""
    SIMILARITY_SCORE_THRESHOLD = 0.55

    song_name = search
    normalized_song_name = _normalize_search_text(song_name)
    if not normalized_song_name:
        return []

    charts = session.exec(select(Chart).where(Chart.title_url.is_not(None))).all()

    ranked_titles: list[tuple[float, str]] = []
    for chart in charts:
        chart_song_name = _normalize_search_text(chart.song_name)
        score = _string_similarity(normalized_song_name, chart_song_name)
        if score >= SIMILARITY_SCORE_THRESHOLD and chart.title_url is not None:
            ranked_titles.append((score, chart.title_url))

    ranked_titles.sort(key=lambda item: item[0], reverse=True)
    return [title_url for _, title_url in ranked_titles]


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
async def create_chart(
    chart: ChartCreate,
    session: SessionDep,
    user: UserDep,
    score_column_id: uuid.UUID | None = None,
    chart_column_id: uuid.UUID | None = None,
    chart_column_player_id: uuid.UUID | None = None,
):
    """Create a new chart"""
    db_chart = Chart.model_validate(chart)

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
    elif chart_column_id is not None and chart_column_player_id is not None:
        db_chart_column = session.get(ChartColumn, chart_column_id)
        if db_chart_column is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Chart column not found"
            )

        db_player = session.get(Player, chart_column_player_id)
        if db_player is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Player not found"
            )

        if not db_chart_column.can_be_edited_by(user):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Permission denied"
            )

        db_chart_column_entry = ChartColumnEntry(
            chart_column=db_chart_column, player=db_player, chart=db_chart
        )

        session.add(db_chart_column_entry)
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="score_column_id or (chart_column_id and chart_column_player_id) must be provided",
        )

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
    """Upload a chart title"""
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


def _string_similarity(left: str, right: str) -> float:
    if not left and not right:
        return 1.0
    if not left or not right:
        return 0.0

    if left in right or right in left:
        return 1.0

    max_length = max(len(left), len(right))
    distance = _levenshtein_distance(left, right)
    return max(0.0, 1.0 - (distance / max_length))


def _levenshtein_distance(left: str, right: str) -> int:
    if left == right:
        return 0
    if not left:
        return len(right)
    if not right:
        return len(left)

    if len(left) < len(right):
        left, right = right, left

    previous_row = list(range(len(right) + 1))
    for left_index, left_char in enumerate(left, start=1):
        current_row = [left_index]
        for right_index, right_char in enumerate(right, start=1):
            insertion_cost = previous_row[right_index] + 1
            deletion_cost = current_row[right_index - 1] + 1
            substitution_cost = previous_row[right_index - 1]
            if left_char != right_char:
                substitution_cost += 1

            current_row.append(min(insertion_cost, deletion_cost, substitution_cost))
        previous_row = current_row

    return previous_row[-1]


def _normalize_search_text(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", text)
    normalized = "".join(char for char in normalized if not unicodedata.combining(char))
    normalized = normalized.casefold()
    normalized = re.sub(r"[^a-z0-9\s]", " ", normalized)
    normalized = re.sub(r"\s+", " ", normalized)
    return normalized.strip()
