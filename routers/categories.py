import uuid
from datetime import date
from fastapi import APIRouter, HTTPException
from sqlmodel import Field, SQLModel, select
from database import SessionDep

router = APIRouter(
    prefix="/categories",
    tags=["categories"]
)


class CategoryBase(SQLModel):
    name: str
    tournament_id: uuid.UUID


class Category(CategoryBase, table=True):
    id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        primary_key=True,
    )


class CategoryCreate(CategoryBase):
    pass


class CategoryPublic(CategoryBase):
    id: uuid.UUID


class CategoryUpdate(SQLModel):
    name: str | None = None
    tournament_id: uuid.UUID | None = None
    


@router.get("/")
async def list_categories(session: SessionDep):
    """List all categories"""
    categories = session.exec(select(Category)).all()
    return categories


@router.get("/{category_id}")
async def get_category(category_id: uuid.UUID, session: SessionDep):
    """Get a specific category"""
    return {"category_id": category_id}


@router.post("/")
async def create_category(category: CategoryCreate, session: SessionDep):
    """Create a new category"""
    db_category = Category.model_validate(category)
    session.add(db_category)
    session.commit()
    session.refresh(db_category)
    return db_category


@router.put("/{category_id}")
async def update_category(category_id: uuid.UUID, category: CategoryUpdate, session: SessionDep):
    """Update a category"""
    return {"category_id": category_id, "message": "Category updated"}


@router.delete("/{category_id}")
async def delete_category(category_id: uuid.UUID, session: SessionDep):
    """Delete a category"""
    return {"category_id": category_id, "message": "Category deleted"}
