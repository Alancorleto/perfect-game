from fastapi import APIRouter

router = APIRouter(
    prefix="/tournaments",
    tags=["tournaments"]
)


@router.get("/")
async def list_tournaments():
    """List all tournaments"""
    return {"message": "List of tournaments"}


@router.get("/{tournament_id}")
async def get_tournament(tournament_id: int):
    """Get a specific tournament"""
    return {"tournament_id": tournament_id}


@router.post("/")
async def create_tournament():
    """Create a new tournament"""
    return {"message": "Tournament created"}


@router.put("/{tournament_id}")
async def update_tournament(tournament_id: int):
    """Update a tournament"""
    return {"tournament_id": tournament_id, "message": "Tournament updated"}


@router.delete("/{tournament_id}")
async def delete_tournament(tournament_id: int):
    """Delete a tournament"""
    return {"tournament_id": tournament_id, "message": "Tournament deleted"}
