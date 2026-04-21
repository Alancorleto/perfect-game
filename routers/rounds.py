import uuid
from fastapi import APIRouter, HTTPException
from sqlmodel import Field, SQLModel, select, Relationship
from models.round import Round, RoundCreate, RoundUpdate, RoundPublic
from models.player import Player
from models.round_player import RoundPlayerLink
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
    for order_index, player_id in enumerate(player_ids):
        db_player = session.get(Player, player_id)
        if not db_player:
            raise HTTPException(status_code=404, detail=f"Player with ID {player_id} not found")
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
