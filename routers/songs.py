import uuid
from typing import Annotated

from fastapi import APIRouter, File, HTTPException
from sqlmodel import select

from database import SessionDep
from image_storage import upload_image
from models.song import Song, SongCreate, SongUpdate

router = APIRouter(prefix="/songs", tags=["songs"])


@router.get("/")
async def list_songs(session: SessionDep):
    """List all songs"""
    songs = session.exec(select(Song)).all()
    return songs


@router.get("/{song_id}")
async def get_song(song_id: uuid.UUID, session: SessionDep):
    """Get a specific song"""
    song = session.get(Song, song_id)
    if not song:
        raise HTTPException(status_code=404, detail="Song not found")
    return song


@router.post("/")
async def create_song(song: SongCreate, session: SessionDep):
    """Create a new song"""
    db_song = Song.model_validate(song)
    session.add(db_song)
    session.commit()
    session.refresh(db_song)
    return db_song


@router.patch("/{song_id}")
async def update_song(song_id: uuid.UUID, song: SongUpdate, session: SessionDep):
    """Update a song"""
    db_song = session.get(Song, song_id)
    if not db_song:
        raise HTTPException(status_code=404, detail="Song not found")
    song_data = song.model_dump(exclude_unset=True)
    db_song.sqlmodel_update(song_data)
    session.add(db_song)
    session.commit()
    session.refresh(db_song)
    return db_song


@router.delete("/{song_id}")
async def delete_song(song_id: uuid.UUID, session: SessionDep):
    """Delete a song"""
    db_song = session.get(Song, song_id)
    if not db_song:
        raise HTTPException(status_code=404, detail="Song not found")
    session.delete(db_song)
    session.commit()
    return {"detail": "Song deleted"}


@router.post("/{song_id}/title")
async def upload_song_title(
    song_id: uuid.UUID, title_file: Annotated[bytes, File()], session: SessionDep
):
    """Upload a song title"""
    db_song = session.get(Song, song_id)
    if not db_song:
        raise HTTPException(status_code=404, detail="Song not found")

    file_name = f"{db_song.id}.png"
    db_song.title_url = await upload_image(title_file, file_name, "titles")

    session.add(db_song)
    session.commit()
    session.refresh(db_song)

    return db_song
