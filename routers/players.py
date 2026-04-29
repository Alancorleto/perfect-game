import uuid
from typing import Annotated

from fastapi import APIRouter, File, HTTPException
from sqlmodel import select

from database import SessionDep
from image_storage import upload_image
from models.player import Player, PlayerCreate, PlayerPublic, PlayerUpdate

router = APIRouter(prefix="/players", tags=["players"])


@router.get("/", response_model=list[PlayerPublic])
async def list_players(session: SessionDep):
    """List all players"""
    players = session.exec(select(Player)).all()
    return players


@router.get("/{player_id}", response_model=PlayerPublic)
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


@router.patch("/{player_id}", response_model=PlayerPublic)
async def update_player(
    player_id: uuid.UUID, player: PlayerUpdate, session: SessionDep
):
    """Update a player"""
    db_player = session.get(Player, player_id)
    if not db_player:
        raise HTTPException(status_code=404, detail="Player not found")
    player_data = player.model_dump(exclude_unset=True)
    db_player.sqlmodel_update(player_data)
    session.add(db_player)
    session.commit()
    session.refresh(db_player)
    return db_player


@router.delete("/{player_id}")
async def delete_player(player_id: uuid.UUID, session: SessionDep):
    """Delete a player"""
    db_player = session.get(Player, player_id)
    if not db_player:
        raise HTTPException(status_code=404, detail="Player not found")
    session.delete(db_player)
    session.commit()
    return {"detail": "Player deleted"}


@router.post("/{player_id}/profile_picture")
async def upload_profile_picture(
    player_id: uuid.UUID, profile_picture: Annotated[bytes, File()], session: SessionDep
):
    """Upload a player's profile picture"""
    db_player = session.get(Player, player_id)
    if not db_player:
        raise HTTPException(status_code=404, detail="Player not found")

    file_name = f"{db_player.id}.png"
    db_player.profile_picture_url = await upload_image(
        profile_picture, file_name, "profile_pictures"
    )

    session.add(db_player)
    session.commit()
    session.refresh(db_player)

    return db_player
