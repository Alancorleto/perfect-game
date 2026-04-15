from datetime import date
import uuid
from fastapi import APIRouter, HTTPException
from sqlalchemy import Column, String
from sqlmodel import Field, SQLModel
from database import SessionDep

router = APIRouter(
    prefix="/players",
    tags=["players"]
)


class PlayerBase(SQLModel):
    nickname: str
    name: str | None = None
    team_name: str | None = None
    birth_date: date | None = None
    country_code: str | None = None
    city: str | None = None
    profile_picture_url: str | None = None


class Player(PlayerBase, table=True):
    id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        primary_key=True,
    )


class PlayerCreate(PlayerBase):
    pass


class PlayerPublic(PlayerBase):
    id: uuid.UUID


class PlayerUpdate(SQLModel):
    nickname: str | None = None
    name: str | None = None
    team_name: str | None = None
    country_code: str | None = None
    city: str | None = None
    profile_picture_url: str | None = None


@router.get("/")
async def list_players(session: SessionDep):
    """List all players"""
    players = session.query(Player).all()
    return players


@router.get("/{player_id}")
async def get_player(player_id: uuid.UUID, session: SessionDep):
    """Get a specific player"""
    db_player = session.get(Player, player_id)
    if not db_player:
        raise HTTPException(status_code=404, detail="Player not found")
    return db_player


@router.post("/", response_model=PlayerPublic)
async def create_player(player: PlayerCreate, session: SessionDep):
    """Create a new player"""
    db_player = Player.model_validate(player)
    session.add(db_player)
    session.commit()
    session.refresh(db_player)
    return db_player


@router.put("/{player_id}", response_model=PlayerPublic)
async def update_player(player_id: uuid.UUID, player: PlayerUpdate, session: SessionDep):
    """Update a player"""
    updated_player = Player(id=player_id, **player.dict(exclude_unset=True))
    return updated_player


@router.delete("/{player_id}")
async def delete_player(player_id: uuid.UUID, session: SessionDep):
    """Delete a player"""
    return {"player_id": player_id, "message": "Player deleted"}
