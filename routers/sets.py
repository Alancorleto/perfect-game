import uuid

from fastapi import APIRouter, HTTPException
from sqlmodel import Field, Relationship, SQLModel, select

from database import SessionDep
from models.chart import Chart
from models.chart_slot import ChartSlot
from models.player import Player
from models.round import Round
from models.score import Score
from models.set import (
    ChartResults,
    PlayerResults,
    Result,
    Set,
    SetCreate,
    SetFormat,
    SetUpdate,
)
from models.set_player import SetPlayerLink

router = APIRouter(prefix="/sets", tags=["sets"])


@router.post("/", response_model=Set)
async def create_set(set: SetCreate, session: SessionDep):
    """Create a new set for a round."""
    round = session.get(Round, set.round_id)
    if not round:
        raise HTTPException(status_code=404, detail="Round not found")

    db_set = Set.model_validate(set)
    session.add(db_set)
    session.commit()
    session.refresh(db_set)
    return db_set


@router.get("/", response_model=list[Set])
async def list_sets(session: SessionDep):
    """List all sets."""
    sets = session.exec(select(Set)).all()
    return sets


@router.get("/{set_id}", response_model=Set)
async def get_set(set_id: uuid.UUID, session: SessionDep):
    """Get a specific set."""
    db_set = session.get(Set, set_id)
    if not db_set:
        raise HTTPException(status_code=404, detail="Set not found")
    return db_set


@router.patch("/{set_id}", response_model=Set)
async def update_set(set_id: uuid.UUID, set: SetUpdate, session: SessionDep):
    """Update a set"""
    db_set = session.get(Set, set_id)
    if not db_set:
        raise HTTPException(status_code=404, detail="Set not found")
    set_data = set.model_dump(exclude_unset=True)
    db_set.sqlmodel_update(set_data)
    session.add(db_set)
    session.commit()
    session.refresh(db_set)
    return db_set


@router.delete("/{set_id}")
async def delete_set(set_id: uuid.UUID, session: SessionDep):
    """Delete a set"""
    db_set = session.get(Set, set_id)
    if not db_set:
        raise HTTPException(status_code=404, detail="Set not found")
    session.delete(db_set)
    session.commit()
    return {"detail": "Set deleted"}


@router.post("/{set_id}/charts")
async def add_chart_to_set(set_id: uuid.UUID, chart_id: uuid.UUID, session: SessionDep):
    """Add a chart to a set"""
    db_set = session.get(Set, set_id)
    if not db_set:
        raise HTTPException(status_code=404, detail="Set not found")

    db_chart = session.get(Chart, chart_id)
    if not db_chart:
        raise HTTPException(status_code=404, detail="Chart not found")

    order_index = len(db_set.chart_slots)

    chart_slot = ChartSlot(
        set=db_set,
        chart=db_chart,
        order_index=order_index,
    )

    db_set.chart_slots.append(chart_slot)

    session.add(chart_slot)
    session.commit()
    session.refresh(chart_slot)

    return chart_slot


@router.put("/{set_id}/charts", response_model=Set)
async def replace_chart_in_set(
    set_id: uuid.UUID,
    chart_order_index: int,
    new_chart_id: uuid.UUID,
    session: SessionDep,
):
    db_set = session.get(Set, set_id)
    if not db_set:
        raise HTTPException(status_code=404, detail="Set not found")

    db_chart = session.get(Chart, new_chart_id)
    if not db_chart:
        raise HTTPException(status_code=404, detail="Chart not found")

    chart_slot = next(
        (
            chart_slot
            for chart_slot in db_set.chart_slots
            if chart_slot.order_index == chart_order_index
        ),
        None,
    )
    if not chart_slot:
        raise HTTPException(status_code=404, detail="Chart slot not found")

    chart_slot.chart = db_chart

    session.add(chart_slot)
    session.commit()
    session.refresh(db_set)

    return db_set


@router.put("/{set_id}/charts/order")
async def update_chart_order_in_set(
    set_id: uuid.UUID, new_chart_slot_order: list[uuid.UUID], session: SessionDep
):
    db_set = session.get(Set, set_id)
    if not db_set:
        raise HTTPException(status_code=404, detail="Set not found")

    if len(new_chart_slot_order) != len(db_set.chart_slots):
        raise HTTPException(
            status_code=400,
            detail="Chart slot order does not match number of chart slots for this set",
        )

    for i, chart_slot_id in enumerate(new_chart_slot_order):
        chart_slot = next(
            (
                chart_slot
                for chart_slot in db_set.chart_slots
                if chart_slot.id == chart_slot_id
            ),
            None,
        )
        if not chart_slot:
            raise HTTPException(
                status_code=404, detail=f"ChartSlot with ID {chart_slot_id} not found"
            )
        chart_slot.order_index = i
        session.add(chart_slot)

    session.commit()
    session.refresh(db_set)

    return db_set


@router.post("/{set_id}/players/bulk")
async def bulk_add_players_to_set(
    set_id: uuid.UUID, player_ids: list[uuid.UUID], session: SessionDep
):
    """Bulk add players to a set"""
    db_set = session.get(Set, set_id)
    if not db_set:
        raise HTTPException(status_code=404, detail="Set not found")

    # Filter out player IDs that are already in the set
    player_ids = filter(
        lambda pid: not any(link.player_id == pid for link in db_set.player_links),
        player_ids,
    )

    previous_player_count = len(db_set.player_links)

    for i, player_id in enumerate(player_ids):
        db_player = session.get(Player, player_id)
        if not db_player:
            raise HTTPException(
                status_code=404, detail=f"Player with ID {player_id} not found"
            )
        order_index = previous_player_count + i
        set_player_link = SetPlayerLink(
            set=db_set, player=db_player, order_index=order_index
        )
        db_set.player_links.append(set_player_link)

    session.add(db_set)
    session.commit()
    session.refresh(db_set)

    return db_set


@router.get("/{set_id}/players", response_model=list[Player])
async def list_players_in_set(set_id: uuid.UUID, session: SessionDep):
    """Get the players for a specific set."""
    set = session.get(Set, set_id)
    if not set:
        raise HTTPException(status_code=404, detail="Set not found")
    players = [player_link.player for player_link in set.player_links]
    return players


@router.get("/{set_id}/results", response_model=list[PlayerResults])
async def get_set_results(set_id: uuid.UUID, session: SessionDep):
    """Get the results for a specific set."""

    set = session.get(Set, set_id)
    if not set:
        raise HTTPException(status_code=404, detail="Set not found")

    chart_slots = sorted(set.chart_slots, key=lambda link: link.order_index)

    chart_results_list: list[ChartResults] = []
    for chart_slot in chart_slots:
        chart_results = _populate_chart_results(chart_slot)
        chart_results_list.append(chart_results)

    player_results_list: list[PlayerResults] = []
    for player_link in set.player_links:
        player_results = _populate_player_results(player_link, chart_results_list)
        player_results_list.append(player_results)

    player_results_list.sort(key=lambda r: (-r.total_score, r.order_index))

    return player_results_list


def _populate_chart_results(chart_slot: ChartSlot) -> ChartResults:
    chart_results = ChartResults(chart_slot_id=chart_slot.id, results=[])

    for score_entry in chart_slot.score_entries:
        result = Result(
            player_id=score_entry.score.player_id,
            set_id=chart_slot.set_id,
            chart_order_index=chart_slot.order_index,
            score=score_entry.score.value,
            score_id=score_entry.score.id,
        )

        chart_results.results.append(result)

    _sort_chart_results(chart_results)

    return chart_results


def _sort_chart_results(chart_results: ChartResults):
    chart_results.results.sort(key=lambda r: (-r.score, r.player_id))

    if len(chart_results.results) > 0:
        chart_results.results[0].place = 1

    # Handle ties
    for i in range(1, len(chart_results.results)):
        result = chart_results.results[i]
        previous_result = chart_results.results[i - 1]

        if result.score == previous_result.score:
            result.is_tie = True
            previous_result.is_tie = True
            result.place = previous_result.place
        else:
            result.place = i + 1


def _populate_player_results(
    player_link: SetPlayerLink, chart_results_list: list[ChartResults]
) -> list[PlayerResults]:
    player = player_link.player
    set = player_link.set

    player_results = PlayerResults(
        player_id=player_link.player_id,
        order_index=player_link.order_index,
    )

    for chart_order_index, chart_results in enumerate(chart_results_list):
        result = _try_get_player_result(player.id, chart_results.results)

        if not result:
            result = Result(
                player_id=player.id,
                set_id=set.id,
                chart_order_index=chart_order_index,
                place=len(chart_results.results) + 1,
            )

        player_results.results.append(result)

    _calculate_player_total_score(player_results, set.format)

    return player_results


def _try_get_player_result(player_id: uuid.UUID, results: list[Result]) -> Result:
    for result in results:
        if result.player_id == player_id:
            return result
    return None


def _calculate_player_total_score(player_results: PlayerResults, set_format: SetFormat):
    if set_format == SetFormat.SCORE_SUM:
        for result in player_results.results:
            player_results.total_score += result.score

    elif set_format == SetFormat.BATTLE:
        for result in player_results.results:
            if result.place == 1 and not result.is_tie and result.score_id is not None:
                player_results.total_score += 1
