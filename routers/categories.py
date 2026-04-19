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
    


@router.get("/")
async def list_categories(session: SessionDep):
    """List all categories"""
    categories = session.exec(select(Category)).all()
    return categories


@router.get("/{category_id}")
async def get_category(category_id: uuid.UUID, session: SessionDep):
    """Get a specific category"""
    db_category = session.get(Category, category_id)
    if not db_category:
        raise HTTPException(status_code=404, detail="Category not found")
    return db_category


@router.post("/")
async def create_category(category: CategoryCreate, session: SessionDep):
    """Create a new category"""
    db_category = Category.model_validate(category)
    session.add(db_category)
    session.commit()
    session.refresh(db_category)
    return db_category


@router.patch("/{category_id}")
async def update_category(category_id: uuid.UUID, category: CategoryUpdate, session: SessionDep):
    """Update a category"""
    db_category = session.get(Category, category_id)
    if not db_category:
        raise HTTPException(status_code=404, detail="Category not found")
    category_data = category.model_dump(exclude_unset=True)
    db_category.sqlmodel_update(category_data)
    session.add(db_category)
    session.commit()
    session.refresh(db_category)
    return db_category


@router.delete("/{category_id}")
async def delete_category(category_id: uuid.UUID, session: SessionDep):
    """Delete a category"""
    return {"category_id": category_id, "message": "Category deleted"}
