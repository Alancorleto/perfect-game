import uuid
from fastapi import APIRouter, HTTPException
from models.song import Song, SongCreate, SongUpdate
from sqlmodel import Field, SQLModel, select, Relationship
from database import SessionDep


router = APIRouter(
    prefix="/songs",
    tags=["songs"]
)


@router.get("/")
async def list_songs():
    """List all songs"""
    return {"message": "List of songs"}


@router.get("/{song_id}")
async def get_song(song_id: int):
    """Get a specific song"""
    return {"song_id": song_id}


@router.post("/")
async def create_song(song: SongCreate, session: SessionDep):
    """Create a new song"""
    db_song = Song.model_validate(song)
    session.add(db_song)
    session.commit()
    session.refresh(db_song)
    return db_song


@router.put("/{song_id}")
async def update_song(song_id: int):
    """Update a song"""
    return {"song_id": song_id, "message": "Song updated"}


@router.delete("/{song_id}")
async def delete_song(song_id: int):
    """Delete a song"""
    return {"song_id": song_id, "message": "Song deleted"}
