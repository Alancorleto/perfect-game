import uuid
from sqlmodel import Field, SQLModel, Relationship
from models.player import Player
from models.tournament import Tournament
from models.category_player import CategoryPlayerLink


class CategoryBase(SQLModel):
    name: str


class Category(CategoryBase, table=True):
    id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        primary_key=True
    )
    tournament_id: uuid.UUID = Field(foreign_key="tournament.id")
    
    players: list[Player] = Relationship(link_model=CategoryPlayerLink)
    tournament: Tournament = Relationship(back_populates="categories")


class CategoryCreate(CategoryBase):
    tournament_id: uuid.UUID


class CategoryPublic(CategoryBase):
    id: uuid.UUID
    tournament_id: uuid.UUID


class CategoryUpdate(SQLModel):
    name: str | None = None