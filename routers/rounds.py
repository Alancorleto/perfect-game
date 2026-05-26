import uuid

from fastapi import APIRouter, HTTPException, status
from sqlmodel import select

from database import SessionDep
from models.category import Category
from models.player import PlayerPublic
from models.round import Round, RoundCreate, RoundPublic, RoundState, RoundUpdate
from models.set import SetPublic
from routers.users import UserDep

router = APIRouter(prefix="/rounds", tags=["rounds"])


@router.get("/", response_model=list[RoundPublic])
async def list_rounds(session: SessionDep):
    """List all rounds"""
    rounds = session.exec(select(Round)).all()
    return rounds


@router.get("/{round_id}", response_model=RoundPublic)
async def get_round(round_id: uuid.UUID, session: SessionDep):
    """Get a specific round"""
    round = session.get(Round, round_id)
    if not round:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Round not found"
        )
    return round


@router.post("/", response_model=RoundPublic)
async def create_round(round: RoundCreate, session: SessionDep, user: UserDep):
    """Create a new round"""
    category = session.get(Category, round.category_id)
    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Category not found"
        )

    if not category.can_be_edited_by(user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not an organizer for this tournament",
        )

    db_round = Round.model_validate(round)

    db_round.order_index = len(category.rounds)

    session.add(db_round)
    session.commit()
    session.refresh(db_round)
    return db_round


@router.patch("/{round_id}", response_model=RoundPublic)
async def update_round(
    round_id: uuid.UUID, round: RoundUpdate, session: SessionDep, user: UserDep
):
    """Update a round"""
    db_round = session.get(Round, round_id)
    if not db_round:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Round not found"
        )

    if not db_round.can_be_edited_by(user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not an organizer for this tournament",
        )

    round_data = round.model_dump(exclude_unset=True)
    db_round.sqlmodel_update(round_data)
    session.add(db_round)
    session.commit()
    session.refresh(db_round)
    return db_round


@router.delete("/{round_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_round(round_id: uuid.UUID, session: SessionDep, user: UserDep):
    """Delete a round"""
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
    db_category = db_round.category

    session.delete(db_round)

    for round in db_category.rounds:
        if round.order_index > round_order_index:
            round.order_index -= 1

    session.commit()


@router.get("/{round_id}/sets", response_model=list[SetPublic])
async def list_sets_in_round(round_id: uuid.UUID, session: SessionDep):
    """Get the set associated with a round"""
    db_round = session.get(Round, round_id)
    if not db_round:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Round not found"
        )
    return sorted(db_round.sets, key=lambda set: set.order_index)


@router.put("/{round_id}/sets/{set_id}/order", response_model=list[SetPublic])
async def change_set_order_in_round(
    round_id: uuid.UUID,
    new_set_order: list[uuid.UUID],
    session: SessionDep,
    user: UserDep,
):
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

    if len(new_set_order) != len(db_round.sets):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The number of sets in the order does not match the number of sets in the round",
        )

    existing_sets = {db_set.id: db_set for db_set in db_round.sets}

    if set(new_set_order) != set(existing_sets.keys()):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The set order does not match the sets in the round",
        )

    for new_index, set_id in enumerate(new_set_order):
        db_set = existing_sets[set_id]
        db_set.order_index = new_index

    session.commit()

    return sorted(db_round.sets, key=lambda set: set.order_index)


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
            detail="You are not an organizer for this tournament",
        )

    for db_set in db_round.sets:
        for db_chart_slot in db_set.chart_slots:
            db_chart_slot.scores = []

    session.add(db_round)
    session.commit()
    session.refresh(db_round)


@router.post("/{round_id}/start", response_model=RoundPublic)
async def start_round(round_id: uuid.UUID, session: SessionDep, user: UserDep):
    """Start a round"""
    db_round = session.get(Round, round_id)
    if not db_round:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Round not found"
        )

    if not db_round.can_be_edited_by(user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not an organizer for this tournament",
        )

    if db_round.state != RoundState.NOT_STARTED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Round has already been started",
        )

    if db_round.order_index > 0:
        db_category = db_round.category
        sorted_rounds = sorted(db_category.rounds, key=lambda r: r.order_index)
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
    """Cancel the start of a round"""
    db_round = session.get(Round, round_id)
    if not db_round:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Round not found"
        )

    if not db_round.can_be_edited_by(user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not an organizer for this tournament",
        )

    if db_round.state != RoundState.IN_PROGRESS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Round is not in progress"
        )

    for db_set in db_round.sets:
        for chart_slot in db_set.chart_slots:
            if len(chart_slot.scores) > 0:
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
    """Pause a round"""
    db_round = session.get(Round, round_id)
    if not db_round:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Round not found"
        )

    if not db_round.can_be_edited_by(user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not an organizer for this tournament",
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
    """Resume a paused round"""
    db_round = session.get(Round, round_id)
    if not db_round:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Round not found"
        )

    if not db_round.can_be_edited_by(user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not an organizer for this tournament",
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
    """Finish a round"""
    db_round = session.get(Round, round_id)
    if not db_round:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Round not found"
        )

    if not db_round.can_be_edited_by(user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not an organizer for this tournament",
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
    """Cancel the finish of a round"""
    db_round = session.get(Round, round_id)
    if not db_round:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Round not found"
        )

    if not db_round.can_be_edited_by(user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not an organizer for this tournament",
        )

    if db_round.state != RoundState.FINISHED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Round is not finished"
        )

    db_category = db_round.category
    if db_round.order_index < len(db_category.rounds) - 1:
        sorted_rounds = sorted(db_category.rounds, key=lambda r: r.order_index)
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
    db_round = session.get(Round, round_id)
    if not db_round:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Round not found"
        )

    qualifying_players = []

    for db_set in sorted(db_round.sets, key=lambda s: s.order_index):
        qualifying_players.extend(db_set.get_qualifying_players())

    return qualifying_players
