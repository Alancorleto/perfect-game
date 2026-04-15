from fastapi import APIRouter

router = APIRouter(
    prefix="/categories",
    tags=["categories"]
)


@router.get("/")
async def list_categories():
    """List all categories"""
    return {"message": "List of categories"}


@router.get("/{category_id}")
async def get_category(category_id: int):
    """Get a specific category"""
    return {"category_id": category_id}


@router.post("/")
async def create_category():
    """Create a new category"""
    return {"message": "Category created"}


@router.put("/{category_id}")
async def update_category(category_id: int):
    """Update a category"""
    return {"category_id": category_id, "message": "Category updated"}


@router.delete("/{category_id}")
async def delete_category(category_id: int):
    """Delete a category"""
    return {"category_id": category_id, "message": "Category deleted"}
