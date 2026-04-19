import uuid
from datetime import date
from fastapi import APIRouter, HTTPException
from sqlmodel import Field, SQLModel, select, Relationship
from database import SessionDep
from routers.players import Player

router = APIRouter(
    prefix="/categories",
    tags=["categories"]
)


class CategoryPlayerLink(SQLModel, table=True):
    category_id: uuid.UUID = Field(foreign_key="category.id", primary_key=True)
    player_id: uuid.UUID = Field(foreign_key="player.id", primary_key=True)


class CategoryBase(SQLModel):
    name: str
    tournament_id: uuid.UUID


class Category(CategoryBase, table=True):
    id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        primary_key=True,
        foreign_key="tournament.id"
    )
    players: list[Player] = Relationship(link_model=CategoryPlayerLink)


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
    db_category = session.get(Category, category_id)
    if not db_category:
        raise HTTPException(status_code=404, detail="Category not found")
    session.delete(db_category)
    session.commit()
    return {"detail": "Category deleted"}


@router.post("/{category_id}/players/bulk")
async def bulk_add_players_to_category(category_id: uuid.UUID, player_ids: list[uuid.UUID], session: SessionDep):
    """Bulk add players to a category"""
    db_category = session.get(Category, category_id)
    if not db_category:
        raise HTTPException(status_code=404, detail="Category not found")
    for player_id in player_ids:
        db_player = session.get(Player, player_id)
        if not db_player:
            raise HTTPException(status_code=404, detail=f"Player with ID {player_id} not found")
        db_category.players.append(db_player)
    session.add(db_category)
    session.commit()
    session.refresh(db_category)
    return db_category

@router.get("/{category_id}/players")
async def list_players_in_category(category_id: uuid.UUID, session: SessionDep):
    """List all players in a category"""
    db_category = session.get(Category, category_id)
    if not db_category:
        raise HTTPException(status_code=404, detail="Category not found")
    return db_category.players
