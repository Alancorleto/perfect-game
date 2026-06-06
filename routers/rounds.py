import uuid

from fastapi import APIRouter, HTTPException, status
from sqlmodel import select

from database import SessionDep
from models.player import PlayerPublic
from models.round import Round, RoundCreate, RoundPublic, RoundState, RoundUpdate
from models.score_table import ScoreTablePublic
from models.tournament import Tournament
from routers.users import UserDep

tag_metadata = {
    "name": "rounds",
    "description": "A round is a stage of competition within a **tournament**. It contains a collection of **score tables**.",
    "externalDocs": {
        "description": "Learn more about rounds here",
        "url": "https://github.com/Alancorleto/perfect-game/blob/main/entities-reference.md#rounds",
    },
}

router = APIRouter(prefix="/rounds", tags=["rounds"])


@router.get("/", response_model=list[RoundPublic])
async def list_rounds(session: SessionDep):
    """List all rounds."""
    rounds = session.exec(select(Round)).all()
    return rounds


@router.get("/{round_id}", response_model=RoundPublic)
async def get_round(round_id: uuid.UUID, session: SessionDep):
    """Get a specific round."""
    round = session.get(Round, round_id)
    if not round:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Round not found"
        )
    return round


@router.post("/", response_model=RoundPublic)
async def create_round(round: RoundCreate, session: SessionDep, user: UserDep):
    """Create a new round for a tournament."""
    tournament = session.get(Tournament, round.tournament_id)
    if not tournament:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Tournament not found"
        )

    if not tournament.can_be_edited_by(user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not an organizer for this event",
        )

    db_round = Round.model_validate(round)

    db_round.order_index = len(tournament.rounds)

    session.add(db_round)
    session.commit()
    session.refresh(db_round)
    return db_round


@router.patch("/{round_id}", response_model=RoundPublic)
async def update_round(
    round_id: uuid.UUID, round: RoundUpdate, session: SessionDep, user: UserDep
):
    """Update a round."""
    db_round = session.get(Round, round_id)
    if not db_round:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Round not found"
        )

    if not db_round.can_be_edited_by(user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not an organizer for this event",
        )

    round_data = round.model_dump(exclude_unset=True)
    db_round.sqlmodel_update(round_data)
    session.add(db_round)
    session.commit()
    session.refresh(db_round)
    return db_round


@router.delete("/{round_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_round(round_id: uuid.UUID, session: SessionDep, user: UserDep):
    """Delete a round. A round can only be deleted if it has not started yet."""
    db_round = session.get(Round, round_id)
    if not db_round:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Round not found"
        )

    if not db_round.can_be_deleted(user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permission denied",
        )

    round_order_index = db_round.order_index
    db_tournament = db_round.tournament

    session.delete(db_round)

    for round in db_tournament.rounds:
        if round.order_index > round_order_index:
            round.order_index -= 1

    session.commit()


@router.get("/{round_id}/score_tables", response_model=list[ScoreTablePublic])
async def list_score_tables_in_round(round_id: uuid.UUID, session: SessionDep):
    """Get the score tables associated with a round by order."""
    db_round = session.get(Round, round_id)
    if not db_round:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Round not found"
        )
    return db_round.get_score_tables_by_order()


@router.put(
    "/{round_id}/score_tables/order",
    response_model=list[ScoreTablePublic],
)
async def change_score_table_order_in_round(
    round_id: uuid.UUID,
    new_score_table_order: list[uuid.UUID],
    session: SessionDep,
    user: UserDep,
):
    """Change the order of score tables in a round.

    The list provided must be the IDs of the score tables in the desired order."""
    db_round = session.get(Round, round_id)

    if not db_round:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Round not found"
        )

    if not db_round.can_be_edited_by(user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to edit this round",
        )

    if len(new_score_table_order) != len(db_round.score_tables):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The number of score tables in the order does not match the number of score tables in the round",
        )

    existing_score_tables = {
        db_score_table.id: db_score_table for db_score_table in db_round.score_tables
    }

    if set(new_score_table_order) != set(existing_score_tables.keys()):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The score table order does not match the score tables in the round",
        )

    for new_index, score_table_id in enumerate(new_score_table_order):
        db_score_table = existing_score_tables[score_table_id]
        db_score_table.order_index = new_index

    session.commit()

    return db_round.get_score_tables_by_order()


@router.delete("/{round_id}/scores", status_code=status.HTTP_204_NO_CONTENT)
async def delete_all_scores_in_round(
    round_id: uuid.UUID, session: SessionDep, user: UserDep
):
    """Delete all scores in a round."""
    db_round = session.get(Round, round_id)
    if not db_round:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Round not found"
        )

    if not db_round.can_be_edited_by(user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not an organizer for this event",
        )

    for db_score_table in db_round.score_tables:
        for db_score_column in db_score_table.score_columns:
            db_score_column.scores = []

    session.add(db_round)
    session.commit()
    session.refresh(db_round)


@router.post("/{round_id}/start", response_model=RoundPublic)
async def start_round(round_id: uuid.UUID, session: SessionDep, user: UserDep):
    """Start a round.

    The round must be in the `not_started` state.

    The new state becomes `in_progress`."""
    db_round = session.get(Round, round_id)
    if not db_round:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Round not found"
        )

    if not db_round.can_be_edited_by(user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not an organizer for this event",
        )

    if db_round.state != RoundState.NOT_STARTED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Round has already been started",
        )

    if db_round.order_index > 0:
        db_tournament = db_round.tournament
        sorted_rounds = db_tournament.get_rounds_by_order()
        previous_round = sorted_rounds[db_round.order_index - 1]

        if not previous_round:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Previous round not found",
            )

        if previous_round.state != RoundState.FINISHED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Previous round must be finished before starting this round",
            )

    db_round.state = RoundState.IN_PROGRESS
    session.add(db_round)
    session.commit()
    session.refresh(db_round)

    return db_round


@router.post("/{round_id}/cancel-start", response_model=RoundPublic)
async def cancel_round_start(round_id: uuid.UUID, session: SessionDep, user: UserDep):
    """Cancel the start of a round.

    The round must be in the `in_progress` state and have no scores.

    The new state becomes `not_started`."""
    db_round = session.get(Round, round_id)
    if not db_round:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Round not found"
        )

    if not db_round.can_be_edited_by(user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not an organizer for this event",
        )

    if db_round.state != RoundState.IN_PROGRESS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Round is not in progress"
        )

    for db_score_table in db_round.score_tables:
        for score_column in db_score_table.score_columns:
            if len(score_column.scores) > 0:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Cannot cancel round with scores",
                )

    db_round.state = RoundState.NOT_STARTED
    session.add(db_round)
    session.commit()
    session.refresh(db_round)

    return db_round


@router.post("/{round_id}/pause", response_model=RoundPublic)
async def pause_round(round_id: uuid.UUID, session: SessionDep, user: UserDep):
    """Pause a round.

    The round must be in the `in_progress` state.

    The new state becomes `paused`."""
    db_round = session.get(Round, round_id)
    if not db_round:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Round not found"
        )

    if not db_round.can_be_edited_by(user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not an organizer for this event",
        )

    if db_round.state != RoundState.IN_PROGRESS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Round is not in progress"
        )

    db_round.state = RoundState.PAUSED
    session.add(db_round)
    session.commit()
    session.refresh(db_round)

    return db_round


@router.post("/{round_id}/unpause", response_model=RoundPublic)
async def unpause_round(round_id: uuid.UUID, session: SessionDep, user: UserDep):
    """Resume a paused round.

    The round must be in the `paused` state.

    The new state becomes `in_progress`."""
    db_round = session.get(Round, round_id)
    if not db_round:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Round not found"
        )

    if not db_round.can_be_edited_by(user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not an organizer for this event",
        )

    if db_round.state != RoundState.PAUSED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Round is not paused"
        )

    db_round.state = RoundState.IN_PROGRESS
    session.add(db_round)
    session.commit()
    session.refresh(db_round)

    return db_round


@router.post("/{round_id}/finish", response_model=RoundPublic)
async def finish_round(round_id: uuid.UUID, session: SessionDep, user: UserDep):
    """Finish a round.

    The round must be in the `in_progress` state.

    The new state becomes `finished`."""
    db_round = session.get(Round, round_id)
    if not db_round:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Round not found"
        )

    if not db_round.can_be_edited_by(user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not an organizer for this event",
        )

    if db_round.state != RoundState.IN_PROGRESS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Round is not in progress"
        )

    db_round.state = RoundState.FINISHED
    session.add(db_round)
    session.commit()
    session.refresh(db_round)

    return db_round


@router.post("/{round_id}/cancel-finish", response_model=RoundPublic)
async def cancel_round_finish(round_id: uuid.UUID, session: SessionDep, user: UserDep):
    """Cancel the finish of a round.

    The round must be in the `finished` state.

    The new state becomes `in_progress`."""
    db_round = session.get(Round, round_id)
    if not db_round:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Round not found"
        )

    if not db_round.can_be_edited_by(user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not an organizer for this event",
        )

    if db_round.state != RoundState.FINISHED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Round is not finished"
        )

    db_tournament = db_round.tournament
    if db_round.order_index < len(db_tournament.rounds) - 1:
        sorted_rounds = db_tournament.get_rounds_by_order()
        next_round = sorted_rounds[db_round.order_index + 1]
        if next_round.state != RoundState.NOT_STARTED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Can't cancel this round if next round is already started",
            )

    db_round.state = RoundState.IN_PROGRESS
    session.add(db_round)
    session.commit()
    session.refresh(db_round)

    return db_round


@router.get("/{round_id}/qualifying-players", response_model=list[PlayerPublic])
async def get_qualifying_players_in_round(
    round_id: uuid.UUID, session: SessionDep, user: UserDep
):
    """List the qualifying players in a round."""

    db_round = session.get(Round, round_id)
    if not db_round:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Round not found"
        )

    return db_round.get_qualifying_players()
