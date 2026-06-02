import uuid

from fastapi import APIRouter, HTTPException, status
from sqlmodel import select

from database import SessionDep
from models.player import Player, PlayerPublic
from models.round import Round
from models.score_column import ScoreColumnPublic
from models.score_table import (
    PlayerResults,
    ScoreTable,
    ScoreTableCreate,
    ScoreTablePublic,
    ScoreTableUpdate,
)
from routers.users import UserDep

description = """
A score table is an entity in which players compare their scores against each other within a **round**.\n
A score table is composed of the **players** that are competing inside it
and the **score columns** that contain the actual scores.\n
A score table can be in any of the following formats:\n
- **score_sum**: the final score is the sum of the scores of the players for each score column\n
- **battle**: the final score is the number of wins of the players for each score column\n
"""

tag_metadata = {
    "name": "score_tables",
    "description": description,
}

router = APIRouter(prefix="/score_tables", tags=["score_tables"])


@router.post("/", response_model=ScoreTablePublic)
async def create_score_table(
    score_table: ScoreTableCreate, session: SessionDep, user: UserDep
):
    """Create a new score table for a round."""
    round = session.get(Round, score_table.round_id)
    if not round:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Round not found"
        )

    if not round.can_be_edited_by(user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not an organizer for this event",
        )

    db_score_table = ScoreTable.model_validate(score_table)

    db_score_table.order_index = len(round.score_tables)

    session.add(db_score_table)
    session.commit()
    session.refresh(db_score_table)
    return db_score_table


@router.get("/", response_model=list[ScoreTablePublic])
async def list_score_tables(session: SessionDep):
    """List all score tables."""
    score_tables = session.exec(select(ScoreTable)).all()
    return score_tables


@router.get("/{score_table_id}", response_model=ScoreTablePublic)
async def get_score_table(score_table_id: uuid.UUID, session: SessionDep):
    """Get a specific score table."""
    db_score_table = session.get(ScoreTable, score_table_id)
    if not db_score_table:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Score table not found"
        )
    return db_score_table


@router.patch("/{score_table_id}", response_model=ScoreTablePublic)
async def update_score_table(
    score_table_id: uuid.UUID,
    score_table: ScoreTableUpdate,
    session: SessionDep,
    user: UserDep,
):
    """Update a score table"""
    db_score_table = session.get(ScoreTable, score_table_id)
    if not db_score_table:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Score table not found"
        )

    if not db_score_table.can_be_edited_by(user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not an organizer for this event",
        )

    score_table_data = score_table.model_dump(exclude_unset=True)
    db_score_table.sqlmodel_update(score_table_data)
    session.add(db_score_table)
    session.commit()
    session.refresh(db_score_table)
    return db_score_table


@router.delete("/{score_table_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_score_table(
    score_table_id: uuid.UUID, session: SessionDep, user: UserDep
):
    """Delete a score table"""
    db_score_table = session.get(ScoreTable, score_table_id)
    if not db_score_table:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Score table not found"
        )

    if not db_score_table.can_be_deleted(user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permission denied",
        )

    score_table_order_index = db_score_table.order_index
    db_round = db_score_table.round

    session.delete(db_score_table)

    for score_table in db_round.score_tables:
        if score_table.order_index > score_table_order_index:
            score_table.order_index -= 1

    session.commit()


@router.get("/{score_table_id}/score_columns", response_model=list[ScoreColumnPublic])
async def list_score_columns_for_score_table(
    score_table_id: uuid.UUID, session: SessionDep
):
    """Get all charts for a score table"""
    db_score_table = session.get(ScoreTable, score_table_id)
    if not db_score_table:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Score table not found"
        )

    return db_score_table.score_columns


@router.put(
    "/{score_table_id}/score_columns/order", response_model=list[ScoreColumnPublic]
)
async def update_score_column_order_in_score_table(
    score_table_id: uuid.UUID,
    new_order: list[uuid.UUID],
    session: SessionDep,
    user: UserDep,
):
    db_score_table = session.get(ScoreTable, score_table_id)
    if not db_score_table:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Score table not found"
        )

    if not db_score_table.can_be_edited_by(user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not an organizer for this event",
        )

    if len(set(new_order)) != len(new_order):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Score column order must not contain duplicate ids",
        )

    score_columns_dict = {column.id: column for column in db_score_table.score_columns}

    if set(new_order) != set(score_columns_dict.keys()):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Score column order must have the same ids as the current score columns",
        )

    for new_index, score_column_id in enumerate(new_order):
        score_column = score_columns_dict[score_column_id]
        score_column.order_index = new_index
        session.add(score_column)

    session.commit()
    session.refresh(db_score_table)

    sorted_score_columns = db_score_table.get_score_columns_by_order()

    return sorted_score_columns


@router.post("/{score_table_id}/players/bulk", response_model=list[PlayerPublic])
async def bulk_add_players_to_score_table(
    score_table_id: uuid.UUID,
    player_ids: list[uuid.UUID],
    session: SessionDep,
    user: UserDep,
):
    """Bulk add players to a score table"""
    db_score_table = session.get(ScoreTable, score_table_id)
    if not db_score_table:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Score table not found"
        )

    if not db_score_table.can_be_edited_by(user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not an organizer for this event",
        )

    # Filter out player IDs that are already in the score table
    player_ids = filter(
        lambda pid: (
            not any(link.player_id == pid for link in db_score_table.player_rows)
        ),
        player_ids,
    )

    for player_id in player_ids:
        db_player = session.get(Player, player_id)
        if not db_player:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Player with ID {player_id} not found",
            )

        db_score_table.add_player(db_player)

    session.add(db_score_table)
    session.commit()
    session.refresh(db_score_table)

    return db_score_table.get_players_by_order()


@router.get("/{score_table_id}/players", response_model=list[PlayerPublic])
async def list_players_in_score_table(score_table_id: uuid.UUID, session: SessionDep):
    """Get the players for a specific score table."""
    score_table = session.get(ScoreTable, score_table_id)
    if not score_table:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Score table not found"
        )
    return score_table.get_players_by_order()


@router.put("/{score_table_id}/players/order", response_model=list[PlayerPublic])
async def update_player_order_in_score_table(
    score_table_id: uuid.UUID,
    player_ids: list[uuid.UUID],
    session: SessionDep,
    user: UserDep,
):
    """Update the order of players in a score table"""
    db_score_table = session.get(ScoreTable, score_table_id)
    if not db_score_table:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Score table not found"
        )

    if not db_score_table.can_be_edited_by(user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not an organizer for this event",
        )

    if len(player_ids) != len(db_score_table.player_rows):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Player IDs count does not match the number of players in the score table",
        )

    for order_index, player_id in enumerate(player_ids):
        # Validate player exists
        db_player = session.get(Player, player_id)
        if not db_player:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Player with ID {player_id} not found",
            )

        # Validate player is in the score table
        player_row = next(
            (row for row in db_score_table.player_rows if row.player_id == player_id),
            None,
        )
        if not player_row:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Player with ID {player_id} is not in the score table",
            )

        # Update the order index
        player_row.order_index = order_index
        session.add(player_row)

    session.commit()
    session.refresh(db_score_table)

    return db_score_table.get_players_by_order()


@router.delete(
    "/{score_table_id}/players/{player_id}", response_model=list[PlayerPublic]
)
async def remove_player_from_score_table(
    score_table_id: uuid.UUID, player_id: uuid.UUID, session: SessionDep, user: UserDep
):
    """Remove a player from a score table."""
    db_score_table = session.get(ScoreTable, score_table_id)
    if not db_score_table:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Score table not found"
        )

    if not db_score_table.can_be_edited_by(user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not an organizer for this event",
        )

    player_row = next(
        (row for row in db_score_table.player_rows if row.player_id == player_id), None
    )
    if not player_row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Player with ID {player_id} is not in the score table",
        )

    player_order_index = player_row.order_index

    # Remove score entries associated with the player
    for score_column in db_score_table.score_columns:
        for score in score_column.scores:
            if score.player_id == player_id:
                session.delete(score)

    session.delete(player_row)

    for player_row in db_score_table.player_rows:
        if player_row.order_index > player_order_index:
            player_row.order_index -= 1
            session.add(player_row)

    session.commit()

    return db_score_table.get_players_by_order()


@router.get("/{score_table_id}/results", response_model=list[PlayerResults])
async def get_score_table_results(score_table_id: uuid.UUID, session: SessionDep):
    """Get the results for a specific score table."""

    score_table = session.get(ScoreTable, score_table_id)
    if not score_table:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Score table not found"
        )

    return score_table.get_results()


@router.get("/{score_table_id}/possible-players", response_model=list[Player])
async def list_possible_players_for_score_table(
    score_table_id: uuid.UUID, session: SessionDep
) -> list[Player]:
    """List all possible players in a score table, including those who passed the previous round."""
    score_table = session.get(ScoreTable, score_table_id)
    if not score_table:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Score table not found"
        )

    current_round = score_table.round
    category = score_table.round.category
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
            if player not in score_table.get_players_by_order()
        ]
    else:
        return [
            player
            for player in previous_round.get_qualifying_players()
            if player not in score_table.get_players_by_order()
        ]
