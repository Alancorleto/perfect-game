import uuid

from fastapi import APIRouter, HTTPException, status
from sqlmodel import select

from database import SessionDep
from models.player import Player, PlayerPublic
from models.round import Round, RoundState
from models.score_column import ScoreColumnPublic
from models.score_table import (
    PlayerResults,
    ScoreTable,
    ScoreTableCreate,
    ScoreTablePublic,
    ScoreTableUpdate,
)
from routers.users import UserDep

tag_metadata = {
    "name": "score_tables",
    "description": "A score table is where players compare their scores against each other within a **round**. It contains a list of players and a list of **score columns**.",
    "externalDocs": {
        "description": "Learn more about score tables here",
        "url": "https://github.com/Alancorleto/perfect-game/blob/main/entities-reference.md#score-tables",
    },
}

router = APIRouter(prefix="/score_tables", tags=["score_tables"])

GET_SCORE_TABLE_RESULTS_EXAMPLE = [
    {
        "player_id": "2f4f3f92-55b2-4c7a-9c3a-8d2d2f6b8c11",
        "player": {
            "id": "2f4f3f92-55b2-4c7a-9c3a-8d2d2f6b8c11",
            "nickname": "Player 1",
            "country_code": "AR",
            "name": "",
            "team_name": "",
            "birth_date": None,
            "city": "",
            "profile_picture_url": "",
            "user_id": None,
            "guest_event_id": "d8d40987-6fcb-40b2-b514-3653feffe278",
        },
        "order_index": 0,
        "results": [
            {
                "player_id": "2f4f3f92-55b2-4c7a-9c3a-8d2d2f6b8c11",
                "player_order_index": 0,
                "score_column_id": "7a8e1c0d-9f6e-4f51-a6aa-7e4a1a0b9c22",
                "score_id": "7a8e1c0d-9f6e-4f51-a6aa-7e4a1a0b9c22",
                "score_value": 998000,
                "place": 1,
                "is_tie": False,
            },
            {
                "player_id": "2f4f3f92-55b2-4c7a-9c3a-8d2d2f6b8c11",
                "player_order_index": 0,
                "score_column_id": "b2b1d4f7-3e8d-4f0f-86dd-1f0d7d6e4c33",
                "score_id": "b2b1d4f7-3e8d-4f0f-86dd-1f0d7d6e4c33",
                "score_value": 997000,
                "place": 2,
                "is_tie": False,
            },
        ],
        "total_score": 1995000,
        "place": 1,
        "is_tie": False,
    },
    {
        "player_id": "8d2f1a0b-6f44-4dbe-9a3c-2d8d9b7c1f02",
        "player": {
            "id": "8d2f1a0b-6f44-4dbe-9a3c-2d8d9b7c1f02",
            "nickname": "Player 2",
            "country_code": "AR",
            "name": "",
            "team_name": "",
            "birth_date": None,
            "city": "",
            "profile_picture_url": "",
            "user_id": None,
            "guest_event_id": "d8d40987-6fcb-40b2-b514-3653feffe278",
        },
        "order_index": 1,
        "results": [
            {
                "player_id": "8d2f1a0b-6f44-4dbe-9a3c-2d8d9b7c1f02",
                "player_order_index": 1,
                "score_column_id": "7a8e1c0d-9f6e-4f51-a6aa-7e4a1a0b9c22",
                "score_id": "7a8e1c0d-9f6e-4f51-a6aa-7e4a1a0b9c22",
                "score_value": 995000,
                "place": 2,
                "is_tie": False,
            },
            {
                "player_id": "8d2f1a0b-6f44-4dbe-9a3c-2d8d9b7c1f02",
                "player_order_index": 1,
                "score_column_id": "b2b1d4f7-3e8d-4f0f-86dd-1f0d7d6e4c33",
                "score_id": "b2b1d4f7-3e8d-4f0f-86dd-1f0d7d6e4c33",
                "score_value": 999000,
                "place": 1,
                "is_tie": False,
            },
        ],
        "total_score": 1994000,
        "place": 2,
        "is_tie": False,
    },
]


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
    """Update a score table."""
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
    """Delete a score table.

    A score table can only be deleted if its associated round has not finished."""
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
    """List all score columns for a score table."""
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
    """Update the order of score columns in a score table.

    The list provided must be the IDs of the score columns in the desired order."""
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
    """Bulk add players to a score table."""
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
    """List all the players for a specific score table."""
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
    """Update the order of players in a score table.

    The list provided must be the IDs of the players in the desired order."""
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
    """Remove a player from a score table.

    A player can only be removed from a score table if the round is not finished."""
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

    if db_score_table.round.state == RoundState.FINISHED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot remove players from a finished round",
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


@router.get(
    "/{score_table_id}/results",
    response_model=list[PlayerResults],
    responses={
        200: {
            "content": {
                "application/json": {"example": GET_SCORE_TABLE_RESULTS_EXAMPLE}
            }
        }
    },
)
async def get_score_table_results(score_table_id: uuid.UUID, session: SessionDep):
    """Get the results for a specific score table.

    It returns a list of results for each player in the score table, ordered by their calculated placing.

    Players with the same final score will have the same placing.

    Each element in the results list inside a player's results, represents a score column and that player's performance in that column.
    """

    score_table = session.get(ScoreTable, score_table_id)
    if not score_table:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Score table not found"
        )

    return score_table.get_results()


@router.get("/{score_table_id}/candidate-players", response_model=list[Player])
async def list_candidate_players_for_score_table(
    score_table_id: uuid.UUID, session: SessionDep
) -> list[Player]:
    """List all candidate players for a score table.

    If the score table is in the first round, all players are considered candidates.

    Otherwise, only players who passed the previous round are considered candidates."""
    score_table = session.get(ScoreTable, score_table_id)
    if not score_table:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Score table not found"
        )

    current_round = score_table.round
    tournament = score_table.round.tournament
    sorted_rounds = tournament.get_rounds_by_order()

    previous_round = (
        sorted_rounds[sorted_rounds.index(current_round) - 1]
        if current_round.order_index > 0
        else None
    )

    if not previous_round:
        return [
            player
            for player in tournament.get_players_by_nickname()
            if player not in score_table.get_players_by_order()
        ]
    else:
        return [
            player
            for player in previous_round.get_qualifying_players()
            if player not in score_table.get_players_by_order()
        ]
