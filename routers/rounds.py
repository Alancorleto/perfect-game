import uuid

from fastapi import APIRouter, HTTPException
from sqlmodel import select

from database import SessionDep
from models.category import Category
from models.round import Round, RoundCreate, RoundState, RoundUpdate
from models.set import Set
from routers.users import UserDep

router = APIRouter(prefix="/rounds", tags=["rounds"])


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
async def create_round(round: RoundCreate, session: SessionDep, user: UserDep):
    """Create a new round"""
    category = session.get(Category, round.category_id)
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")

    if not category.has_organizer(user):
        raise HTTPException(
            status_code=403, detail="You are not an organizer for this tournament"
        )

    db_round = Round.model_validate(round)

    session.add(db_round)
    session.commit()
    session.refresh(db_round)
    return db_round


@router.patch("/{round_id}")
async def update_round(
    round_id: uuid.UUID, round: RoundUpdate, session: SessionDep, user: UserDep
):
    """Update a round"""
    db_round = session.get(Round, round_id)
    if not db_round:
        raise HTTPException(status_code=404, detail="Round not found")

    if not db_round.has_organizer(user):
        raise HTTPException(
            status_code=403, detail="You are not an organizer for this tournament"
        )

    round_data = round.model_dump(exclude_unset=True)
    db_round.sqlmodel_update(round_data)
    session.add(db_round)
    session.commit()
    session.refresh(db_round)
    return db_round


@router.delete("/{round_id}")
async def delete_round(round_id: uuid.UUID, session: SessionDep, user: UserDep):
    """Delete a round"""
    db_round = session.get(Round, round_id)
    if not db_round:
        raise HTTPException(status_code=404, detail="Round not found")

    if not db_round.has_organizer(user):
        raise HTTPException(
            status_code=403, detail="You are not an organizer for this tournament"
        )

    session.delete(db_round)
    session.commit()
    return {"detail": "Round deleted"}


@router.get("/{round_id}/sets", response_model=list[Set])
async def list_sets_in_round(round_id: uuid.UUID, session: SessionDep):
    """Get the set associated with a round"""
    db_round = session.get(Round, round_id)
    if not db_round:
        raise HTTPException(status_code=404, detail="Round not found")
    return db_round.sets


@router.post("/{round_id}/start")
async def start_round(round_id: uuid.UUID, session: SessionDep, user: UserDep):
    """Start a round"""
    db_round = session.get(Round, round_id)
    if not db_round:
        raise HTTPException(status_code=404, detail="Round not found")

    if not db_round.has_organizer(user):
        raise HTTPException(
            status_code=403, detail="You are not an organizer for this tournament"
        )

    if db_round.state != RoundState.NOT_STARTED:
        raise HTTPException(status_code=400, detail="Round has already been started")

    db_round.state = RoundState.IN_PROGRESS
    session.add(db_round)
    session.commit()
    session.refresh(db_round)

    return db_round


@router.post("/{round_id}/cancel-start")
async def cancel_round_start(round_id: uuid.UUID, session: SessionDep, user: UserDep):
    """Cancel the start of a round"""
    db_round = session.get(Round, round_id)
    if not db_round:
        raise HTTPException(status_code=404, detail="Round not found")

    if not db_round.has_organizer(user):
        raise HTTPException(
            status_code=403, detail="You are not an organizer for this tournament"
        )

    if db_round.state != RoundState.IN_PROGRESS:
        raise HTTPException(status_code=400, detail="Round is not in progress")

    db_round.state = RoundState.NOT_STARTED
    session.add(db_round)
    session.commit()
    session.refresh(db_round)

    return db_round


@router.post("/{round_id}/pause")
async def pause_round(round_id: uuid.UUID, session: SessionDep, user: UserDep):
    """Pause a round"""
    db_round = session.get(Round, round_id)
    if not db_round:
        raise HTTPException(status_code=404, detail="Round not found")

    if not db_round.has_organizer(user):
        raise HTTPException(
            status_code=403, detail="You are not an organizer for this tournament"
        )

    if db_round.state != RoundState.IN_PROGRESS:
        raise HTTPException(status_code=400, detail="Round is not in progress")

    db_round.state = RoundState.PAUSED
    session.add(db_round)
    session.commit()
    session.refresh(db_round)

    return db_round


@router.post("/{round_id}/unpause")
async def unpause_round(round_id: uuid.UUID, session: SessionDep, user: UserDep):
    """Resume a paused round"""
    db_round = session.get(Round, round_id)
    if not db_round:
        raise HTTPException(status_code=404, detail="Round not found")

    if not db_round.has_organizer(user):
        raise HTTPException(
            status_code=403, detail="You are not an organizer for this tournament"
        )

    if db_round.state != RoundState.PAUSED:
        raise HTTPException(status_code=400, detail="Round is not paused")

    db_round.state = RoundState.IN_PROGRESS
    session.add(db_round)
    session.commit()
    session.refresh(db_round)

    return db_round


@router.post("/{round_id}/finish")
async def finish_round(round_id: uuid.UUID, session: SessionDep, user: UserDep):
    """Finish a round"""
    db_round = session.get(Round, round_id)
    if not db_round:
        raise HTTPException(status_code=404, detail="Round not found")

    if not db_round.has_organizer(user):
        raise HTTPException(
            status_code=403, detail="You are not an organizer for this tournament"
        )

    if db_round.state != RoundState.IN_PROGRESS:
        raise HTTPException(status_code=400, detail="Round is not in progress")

    db_round.state = RoundState.FINISHED
    session.add(db_round)
    session.commit()
    session.refresh(db_round)

    return db_round


@router.post("/{round_id}/cancel-finish")
async def cancel_round_finish(round_id: uuid.UUID, session: SessionDep, user: UserDep):
    """Cancel the finish of a round"""
    db_round = session.get(Round, round_id)
    if not db_round:
        raise HTTPException(status_code=404, detail="Round not found")

    if not db_round.has_organizer(user):
        raise HTTPException(
            status_code=403, detail="You are not an organizer for this tournament"
        )

    if db_round.state != RoundState.FINISHED:
        raise HTTPException(status_code=400, detail="Round is not finished")

    db_round.state = RoundState.IN_PROGRESS
    session.add(db_round)
    session.commit()
    session.refresh(db_round)

    return db_round
