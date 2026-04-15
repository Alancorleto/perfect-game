from fastapi import APIRouter

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
async def create_song():
    """Create a new song"""
    return {"message": "Song created"}


@router.put("/{song_id}")
async def update_song(song_id: int):
    """Update a song"""
    return {"song_id": song_id, "message": "Song updated"}


@router.delete("/{song_id}")
async def delete_song(song_id: int):
    """Delete a song"""
    return {"song_id": song_id, "message": "Song deleted"}
