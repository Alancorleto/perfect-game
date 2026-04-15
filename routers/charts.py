from fastapi import APIRouter

router = APIRouter(
    prefix="/charts",
    tags=["charts"]
)


@router.get("/")
async def list_charts():
    """List all charts"""
    return {"message": "List of charts"}


@router.get("/{chart_id}")
async def get_chart(chart_id: int):
    """Get a specific chart"""
    return {"chart_id": chart_id}


@router.post("/")
async def create_chart():
    """Create a new chart"""
    return {"message": "Chart created"}


@router.put("/{chart_id}")
async def update_chart(chart_id: int):
    """Update a chart"""
    return {"chart_id": chart_id, "message": "Chart updated"}


@router.delete("/{chart_id}")
async def delete_chart(chart_id: int):
    """Delete a chart"""
    return {"chart_id": chart_id, "message": "Chart deleted"}
