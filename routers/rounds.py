import uuid
from fastapi import APIRouter, HTTPException
from sqlmodel import Field, SQLModel, select, Relationship
from models.chart import Chart
from models.round import Round, RoundCreate, RoundState, RoundUpdate, RoundPublic
from models.player import Player
from models.round_player import RoundPlayerLink
from models.round_chart import RoundChartLink
from database import SessionDep

router = APIRouter(
    prefix="/rounds",
    tags=["rounds"]
)


@router.get("/")
async def list_rounds(session: SessionDep):
    """List all rounds"""
    rounds = session.exec(select(Round)).all()
    return rounds


@router.get("/{round_id}")
async def get_round(round_id: uuid.UUID, session: SessionDep):
    """Get a specific round"""
    round = session.get(Round, round_id)
    if not round:
        raise HTTPException(status_code=404, detail="Round not found")
    return round


@router.post("/")
async def create_round(round: RoundCreate, session: SessionDep):
    """Create a new round"""
    db_round = Round.model_validate(round)
    session.add(db_round)
    session.commit()
    session.refresh(db_round)
    return db_round


@router.patch("/{round_id}")
async def update_round(round_id: uuid.UUID, round: RoundUpdate, session: SessionDep):
    """Update a round"""
    db_round = session.get(Round, round_id)
    if not db_round:
        raise HTTPException(status_code=404, detail="Round not found")
    round_data = round.model_dump(exclude_unset=True)
    db_round.sqlmodel_update(round_data)
    session.add(db_round)
    session.commit()
    session.refresh(db_round)
    return db_round


@router.delete("/{round_id}")
async def delete_round(round_id: uuid.UUID, session: SessionDep):
    """Delete a round"""
    db_round = session.get(Round, round_id)
    if not db_round:
        raise HTTPException(status_code=404, detail="Round not found")
    session.delete(db_round)
    session.commit()
    return {"detail": "Round deleted"}


@router.post("/{category_id}/players/bulk")
async def bulk_add_players_to_round(round_id: uuid.UUID, player_ids: list[uuid.UUID], session: SessionDep):
    """Bulk add players to a round"""
    db_round = session.get(Round, round_id)
    if not db_round:
        raise HTTPException(status_code=404, detail="Round not found")
    
    # Filter out player IDs that are already in the round
    player_ids = filter(
        lambda pid: not any(link.player_id == pid for link in db_round.player_links),
        player_ids
    )

    previous_player_count = len(db_round.player_links)

    for i, player_id in enumerate(player_ids):
        db_player = session.get(Player, player_id)
        if not db_player:
            raise HTTPException(status_code=404, detail=f"Player with ID {player_id} not found")
        order_index = previous_player_count + i
        db_round_player_link = RoundPlayerLink(round=db_round, player=db_player, order_index=order_index)
        db_round.player_links.append(db_round_player_link)
    session.add(db_round)
    session.commit()
    session.refresh(db_round)
    return db_round


@router.get("/{round_id}/players")
async def list_players_in_round(round_id: uuid.UUID, session: SessionDep):
    """List all players in a round"""
    db_round = session.get(Round, round_id)
    if not db_round:
        raise HTTPException(status_code=404, detail="Round not found")
    sorted_players = sorted(db_round.player_links, key=lambda link: link.order_index)
    return [link.player for link in sorted_players]


@router.put("/{round_id}/players/order")
async def update_player_order_in_round(round_id: uuid.UUID, player_ids: list[uuid.UUID], session: SessionDep):
    """Update the order of players in a round"""
    db_round = session.get(Round, round_id)
    if not db_round:
        raise HTTPException(status_code=404, detail="Round not found")
    
    if len(player_ids) != len(db_round.player_links):
        raise HTTPException(status_code=400, detail="Player IDs count does not match the number of players in the round")
    
    for order_index, player_id in enumerate(player_ids):
        # Validate player exists
        db_player = session.get(Player, player_id)
        if not db_player:
            raise HTTPException(status_code=404, detail=f"Player with ID {player_id} not found")

        # Validate player is in the round
        db_round_player_link = next((link for link in db_round.player_links if link.player_id == player_id), None)
        if not db_round_player_link:
            raise HTTPException(status_code=404, detail=f"Player with ID {player_id} is not in the round")
    
        # Update the order index
        db_round_player_link.order_index = order_index
        session.add(db_round_player_link)

    session.commit()
    session.refresh(db_round)
    return db_round


@router.delete("/{round_id}/players/{player_id}")
async def remove_player_from_round(round_id: uuid.UUID, player_id: uuid.UUID, session: SessionDep):
    """Remove a player from a round"""
    db_round = session.get(Round, round_id)
    if not db_round:
        raise HTTPException(status_code=404, detail="Round not found")
    
    db_player = session.get(Player, player_id)
    if not db_player:
        raise HTTPException(status_code=404, detail="Player not found")
    
    db_round_player_link = next((link for link in db_round.player_links if link.player_id == player_id), None)
    if not db_round_player_link:
        raise HTTPException(status_code=404, detail="Player is not in the round")
    
    session.delete(db_round_player_link)
    
    # Update order indices of remaining players
    for link in db_round.player_links:
        if link.order_index > db_round_player_link.order_index:
            link.order_index -= 1
            session.add(link)
    
    session.commit()
    session.refresh(db_round)
    
    return db_round


@router.post("/{round_id}/charts")
async def add_chart_to_round(round_id: uuid.UUID, chart_id: uuid.UUID, session: SessionDep):
    """Add a chart to a round"""
    db_round = session.get(Round, round_id)
    if not db_round:
        raise HTTPException(status_code=404, detail="Round not found")
    
    db_chart = session.get(Chart, chart_id)
    if not db_chart:
        raise HTTPException(status_code=404, detail="Chart not found")
    
    # Check if chart is already in the round
    if any(link.chart_id == chart_id for link in db_round.chart_links):
        raise HTTPException(status_code=400, detail="Chart is already in the round")
    
    order_index = len(db_round.chart_links)
    db_round_chart_link = RoundChartLink(round=db_round, chart=db_chart, order_index=order_index)
    db_round.chart_links.append(db_round_chart_link)
    
    session.add(db_round)
    session.commit()
    session.refresh(db_round)
    
    return db_round


@router.get("/{round_id}/charts")
async def list_charts_in_round(round_id: uuid.UUID, session: SessionDep):
    """List all charts in a round"""
    db_round = session.get(Round, round_id)
    if not db_round:
        raise HTTPException(status_code=404, detail="Round not found")
    sorted_charts = sorted(db_round.chart_links, key=lambda link: link.order_index)
    return [link.chart for link in sorted_charts]


@router.put("/{round_id}/charts/{old_chart_id}/replace")
async def replace_chart_in_round(round_id: uuid.UUID, old_chart_id: uuid.UUID, new_chart_id: uuid.UUID, session: SessionDep):
    """Replace a chart in a round with another chart"""
    db_round = session.get(Round, round_id)
    if not db_round:
        raise HTTPException(status_code=404, detail="Round not found")
    
    db_old_chart = session.get(Chart, old_chart_id)
    if not db_old_chart:
        raise HTTPException(status_code=404, detail="Old chart not found")
    
    db_new_chart = session.get(Chart, new_chart_id)
    if not db_new_chart:
        raise HTTPException(status_code=404, detail="New chart not found")
    
    db_round_chart_link = next((link for link in db_round.chart_links if link.chart_id == old_chart_id), None)
    if not db_round_chart_link:
        raise HTTPException(status_code=404, detail="Old chart is not in the round")
    
    # Check if new chart is already in the round
    if any(link.chart_id == new_chart_id for link in db_round.chart_links):
        raise HTTPException(status_code=400, detail="New chart is already in the round")
    
    db_round_chart_link.chart = db_new_chart
    session.add(db_round_chart_link)
    session.commit()
    session.refresh(db_round)
    
    return db_round


@router.put("/{round_id}/charts/order")
async def update_chart_order_in_round(round_id: uuid.UUID, chart_ids: list[uuid.UUID], session: SessionDep):
    """Update the order of charts in a round"""
    db_round = session.get(Round, round_id)
    if not db_round:
        raise HTTPException(status_code=404, detail="Round not found")
    
    if len(chart_ids) != len(db_round.chart_links):
        raise HTTPException(status_code=400, detail="Chart IDs count does not match the number of charts in the round")
    
    for order_index, chart_id in enumerate(chart_ids):
        # Validate chart exists
        db_chart = session.get(Chart, chart_id)
        if not db_chart:
            raise HTTPException(status_code=404, detail=f"Chart with ID {chart_id} not found")

        # Validate chart is in the round
        db_round_chart_link = next((link for link in db_round.chart_links if link.chart_id == chart_id), None)
        if not db_round_chart_link:
            raise HTTPException(status_code=404, detail=f"Chart with ID {chart_id} is not in the round")
    
        # Update the order index
        db_round_chart_link.order_index = order_index
        session.add(db_round_chart_link)

    session.commit()
    session.refresh(db_round)
    return db_round


@router.delete("/{round_id}/charts/{chart_id}")
async def remove_chart_from_round(round_id: uuid.UUID, chart_id: uuid.UUID, session: SessionDep):
    """Remove a chart from a round"""
    db_round = session.get(Round, round_id)
    if not db_round:
        raise HTTPException(status_code=404, detail="Round not found")
    
    db_chart = session.get(Chart, chart_id)
    if not db_chart:
        raise HTTPException(status_code=404, detail="Chart not found")
    
    db_round_chart_link = next((link for link in db_round.chart_links if link.chart_id == chart_id), None)
    if not db_round_chart_link:
        raise HTTPException(status_code=404, detail="Chart is not in the round")
    
    session.delete(db_round_chart_link)
    
    # Update order indices of remaining charts
    for link in db_round.chart_links:
        if link.order_index > db_round_chart_link.order_index:
            link.order_index -= 1
            session.add(link)
    
    session.commit()
    session.refresh(db_round)
    
    return db_round


@router.post("/{round_id}/start")
async def start_round(round_id: uuid.UUID, session: SessionDep):
    """Start a round"""
    db_round = session.get(Round, round_id)
    if not db_round:
        raise HTTPException(status_code=404, detail="Round not found")
    
    if db_round.state != RoundState.NOT_STARTED:
        raise HTTPException(status_code=400, detail="Round has already been started")
    
    db_round.state = RoundState.IN_PROGRESS
    session.add(db_round)
    session.commit()
    session.refresh(db_round)
    
    return db_round


@router.post("/{round_id}/cancel-start")
async def cancel_round_start(round_id: uuid.UUID, session: SessionDep):
    """Cancel the start of a round"""
    db_round = session.get(Round, round_id)
    if not db_round:
        raise HTTPException(status_code=404, detail="Round not found")

    if db_round.state != RoundState.IN_PROGRESS:
        raise HTTPException(status_code=400, detail="Round is not in progress")

    db_round.state = RoundState.NOT_STARTED
    session.add(db_round)
    session.commit()
    session.refresh(db_round)

    return db_round


@router.post("/{round_id}/pause")
async def pause_round(round_id: uuid.UUID, session: SessionDep):
    """Pause a round"""
    db_round = session.get(Round, round_id)
    if not db_round:
        raise HTTPException(status_code=404, detail="Round not found")

    if db_round.state != RoundState.IN_PROGRESS:
        raise HTTPException(status_code=400, detail="Round is not in progress")

    db_round.state = RoundState.PAUSED
    session.add(db_round)
    session.commit()
    session.refresh(db_round)

    return db_round


@router.post("/{round_id}/unpause")
async def unpause_round(round_id: uuid.UUID, session: SessionDep):
    """Resume a paused round"""
    db_round = session.get(Round, round_id)
    if not db_round:
        raise HTTPException(status_code=404, detail="Round not found")

    if db_round.state != RoundState.PAUSED:
        raise HTTPException(status_code=400, detail="Round is not paused")

    db_round.state = RoundState.IN_PROGRESS
    session.add(db_round)
    session.commit()
    session.refresh(db_round)

    return db_round


@router.post("/{round_id}/finish")
async def finish_round(round_id: uuid.UUID, session: SessionDep):
    """Finish a round"""
    db_round = session.get(Round, round_id)
    if not db_round:
        raise HTTPException(status_code=404, detail="Round not found")

    if db_round.state != RoundState.IN_PROGRESS:
        raise HTTPException(status_code=400, detail="Round is not in progress")

    db_round.state = RoundState.FINISHED
    session.add(db_round)
    session.commit()
    session.refresh(db_round)

    return db_round
