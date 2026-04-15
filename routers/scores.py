from fastapi import APIRouter

router = APIRouter(
    prefix="/scores",
    tags=["scores"]
)


@router.get("/")
async def list_scores():
    """List all scores"""
    return {"message": "List of scores"}


@router.get("/{score_id}")
async def get_score(score_id: int):
    """Get a specific score"""
    return {"score_id": score_id}


@router.post("/")
async def create_score():
    """Create a new score"""
    return {"message": "Score created"}


@router.put("/{score_id}")
async def update_score(score_id: int):
    """Update a score"""
    return {"score_id": score_id, "message": "Score updated"}


@router.delete("/{score_id}")
async def delete_score(score_id: int):
    """Delete a score"""
    return {"score_id": score_id, "message": "Score deleted"}
