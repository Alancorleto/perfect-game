from fastapi import APIRouter

router = APIRouter(
    prefix="/rounds",
    tags=["rounds"]
)


@router.get("/")
async def list_rounds():
    """List all rounds"""
    return {"message": "List of rounds"}


@router.get("/{round_id}")
async def get_round(round_id: int):
    """Get a specific round"""
    return {"round_id": round_id}


@router.post("/")
async def create_round():
    """Create a new round"""
    return {"message": "Round created"}


@router.put("/{round_id}")
async def update_round(round_id: int):
    """Update a round"""
    return {"round_id": round_id, "message": "Round updated"}


@router.delete("/{round_id}")
async def delete_round(round_id: int):
    """Delete a round"""
    return {"round_id": round_id, "message": "Round deleted"}
