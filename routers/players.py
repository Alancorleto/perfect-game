from fastapi import APIRouter

router = APIRouter(
    prefix="/players",
    tags=["players"]
)


@router.get("/")
async def list_players():
    """List all players"""
    return {"message": "List of players"}


@router.get("/{player_id}")
async def get_player(player_id: int):
    """Get a specific player"""
    return {"player_id": player_id}


@router.post("/")
async def create_player():
    """Create a new player"""
    return {"message": "Player created"}


@router.put("/{player_id}")
async def update_player(player_id: int):
    """Update a player"""
    return {"player_id": player_id, "message": "Player updated"}


@router.delete("/{player_id}")
async def delete_player(player_id: int):
    """Delete a player"""
    return {"player_id": player_id, "message": "Player deleted"}
