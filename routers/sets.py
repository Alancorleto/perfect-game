import uuid

from fastapi import APIRouter, HTTPException, status
from sqlmodel import select

from database import SessionDep
from models.chart_slot import ChartSlot, ChartSlotPublic
from models.player import Player, PlayerPublic
from models.round import Round
from models.set import (
    ChartResults,
    PlayerResults,
    Result,
    Set,
    SetCreate,
    SetFormat,
    SetPublic,
    SetUpdate,
)
from models.set_player import SetPlayerLink
from routers.users import UserDep

router = APIRouter(prefix="/sets", tags=["sets"])


@router.post("/", response_model=SetPublic)
async def create_set(set: SetCreate, session: SessionDep, user: UserDep):
    """Create a new set for a round."""
    round = session.get(Round, set.round_id)
    if not round:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Round not found"
        )

    if not round.can_be_edited_by(user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not an organizer for this tournament",
        )

    db_set = Set.model_validate(set)

    db_set.order_index = len(round.sets)

    session.add(db_set)
    session.commit()
    session.refresh(db_set)
    return db_set


@router.get("/", response_model=list[SetPublic])
async def list_sets(session: SessionDep):
    """List all sets."""
    sets = session.exec(select(Set)).all()
    return sets


@router.get("/{set_id}", response_model=SetPublic)
async def get_set(set_id: uuid.UUID, session: SessionDep):
    """Get a specific set."""
    db_set = session.get(Set, set_id)
    if not db_set:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Set not found"
        )
    return db_set


@router.patch("/{set_id}", response_model=SetPublic)
async def update_set(
    set_id: uuid.UUID, set: SetUpdate, session: SessionDep, user: UserDep
):
    """Update a set"""
    db_set = session.get(Set, set_id)
    if not db_set:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Set not found"
        )

    if not db_set.can_be_edited_by(user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not an organizer for this tournament",
        )

    set_data = set.model_dump(exclude_unset=True)
    db_set.sqlmodel_update(set_data)
    session.add(db_set)
    session.commit()
    session.refresh(db_set)
    return db_set


@router.delete("/{set_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_set(set_id: uuid.UUID, session: SessionDep, user: UserDep):
    """Delete a set"""
    db_set = session.get(Set, set_id)
    if not db_set:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Set not found"
        )

    if not db_set.can_be_deleted(user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permission denied",
        )

    set_order_index = db_set.order_index
    db_round = db_set.round

    session.delete(db_set)

    for set in db_round.sets:
        if set.order_index > set_order_index:
            set.order_index -= 1

    session.commit()


@router.get("/{set_id}/chart_slots", response_model=list[ChartSlotPublic])
async def list_chart_slots_for_set(set_id: uuid.UUID, session: SessionDep):
    """Get all charts for a set"""
    db_set = session.get(Set, set_id)
    if not db_set:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Set not found"
        )

    return db_set.chart_slots


@router.put("/{set_id}/chart_slots/order", response_model=list[ChartSlotPublic])
async def update_chart_slot_order_in_set(
    set_id: uuid.UUID,
    new_order: list[uuid.UUID],
    session: SessionDep,
    user: UserDep,
):
    db_set = session.get(Set, set_id)
    if not db_set:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Set not found"
        )

    if not db_set.can_be_edited_by(user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not an organizer for this tournament",
        )

    if len(set(new_order)) != len(new_order):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Chart slot order must not contain duplicate ids",
        )

    chart_slots_dict = {slot.id: slot for slot in db_set.chart_slots}

    if set(new_order) != set(chart_slots_dict.keys()):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Chart slot order must have the same ids as the current chart slots",
        )

    for new_index, chart_slot_id in enumerate(new_order):
        chart_slot = chart_slots_dict[chart_slot_id]
        chart_slot.order_index = new_index
        session.add(chart_slot)

    session.commit()
    session.refresh(db_set)

    sorted_chart_slots = db_set.get_chart_slots_by_order()

    return sorted_chart_slots


@router.post("/{set_id}/players/bulk", response_model=list[PlayerPublic])
async def bulk_add_players_to_set(
    set_id: uuid.UUID, player_ids: list[uuid.UUID], session: SessionDep, user: UserDep
):
    """Bulk add players to a set"""
    db_set = session.get(Set, set_id)
    if not db_set:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Set not found"
        )

    if not db_set.can_be_edited_by(user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not an organizer for this tournament",
        )

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
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Player with ID {player_id} not found",
            )
        order_index = previous_player_count + i
        set_player_link = SetPlayerLink(
            set=db_set, player=db_player, order_index=order_index
        )
        db_set.player_links.append(set_player_link)

    session.add(db_set)
    session.commit()
    session.refresh(db_set)

    return db_set.get_players_by_order()


@router.get("/{set_id}/players", response_model=list[PlayerPublic])
async def list_players_in_set(set_id: uuid.UUID, session: SessionDep):
    """Get the players for a specific set."""
    set = session.get(Set, set_id)
    if not set:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Set not found"
        )
    return set.get_players_by_order()


@router.put("/{set_id}/players/order", response_model=list[PlayerPublic])
async def update_player_order_in_set(
    set_id: uuid.UUID, player_ids: list[uuid.UUID], session: SessionDep, user: UserDep
):
    """Update the order of players in a set"""
    db_set = session.get(Set, set_id)
    if not db_set:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Set not found"
        )

    if not db_set.can_be_edited_by(user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not an organizer for this tournament",
        )

    if len(player_ids) != len(db_set.player_links):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Player IDs count does not match the number of players in the set",
        )

    for order_index, player_id in enumerate(player_ids):
        # Validate player exists
        db_player = session.get(Player, player_id)
        if not db_player:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Player with ID {player_id} not found",
            )

        # Validate player is in the set
        db_set_player_link = next(
            (link for link in db_set.player_links if link.player_id == player_id), None
        )
        if not db_set_player_link:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Player with ID {player_id} is not in the set",
            )

        # Update the order index
        db_set_player_link.order_index = order_index
        session.add(db_set_player_link)

    session.commit()
    session.refresh(db_set)

    return db_set.get_players_by_order()


@router.delete("/{set_id}/players/{player_id}", response_model=list[PlayerPublic])
async def remove_player_from_set(
    set_id: uuid.UUID, player_id: uuid.UUID, session: SessionDep, user: UserDep
):
    """Remove a player from a set."""
    db_set = session.get(Set, set_id)
    if not db_set:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Set not found"
        )

    if not db_set.can_be_edited_by(user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not an organizer for this tournament",
        )

    db_set_player_link = next(
        (link for link in db_set.player_links if link.player_id == player_id), None
    )
    if not db_set_player_link:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Player with ID {player_id} is not in the set",
        )

    player_order_index = db_set_player_link.order_index

    # Remove score entries associated with the player
    for chart_slot in db_set.chart_slots:
        for score in chart_slot.scores:
            if score.player_id == player_id:
                session.delete(score)

    session.delete(db_set_player_link)

    for player_link in db_set.player_links:
        if player_link.order_index > player_order_index:
            player_link.order_index -= 1
            session.add(player_link)

    session.commit()

    return db_set.get_players_by_order()


@router.get("/{set_id}/results", response_model=list[PlayerResults])
async def get_set_results(set_id: uuid.UUID, session: SessionDep):
    """Get the results for a specific set."""

    set = session.get(Set, set_id)
    if not set:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Set not found"
        )

    return set.get_results()


@router.get("/{set_id}/possible-players", response_model=list[Player])
async def list_possible_players_for_set(
    set_id: uuid.UUID, session: SessionDep
) -> list[Player]:
    """List all possible players in a set, including those who passed the previous round."""
    set = session.get(Set, set_id)
    if not set:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Set not found"
        )

    current_round = set.round
    category = set.round.category
    sorted_rounds = category.get_rounds_by_order()

    previous_round = (
        sorted_rounds[sorted_rounds.index(current_round) - 1]
        if current_round.order_index > 0
        else None
    )

    if not previous_round:
        return [
            player
            for player in category.get_players_by_nickname()
            if player not in set.get_players_by_order()
        ]
    else:
        return [
            player
            for player in previous_round.get_qualifying_players()
            if player not in set.get_players_by_order()
        ]
