import uuid
from typing import TYPE_CHECKING

from sqlmodel import Field, Relationship, SQLModel

from models.category_player import CategoryPlayerLink
from models.player import Player
from models.tournament import Tournament
from models.user import User

if TYPE_CHECKING:
    from models.round import Round


class CategoryBase(SQLModel):
    name: str


class Category(CategoryBase, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    tournament_id: uuid.UUID = Field(foreign_key="tournament.id")

    players: list[Player] = Relationship(link_model=CategoryPlayerLink)
    tournament: Tournament = Relationship(back_populates="categories")
    rounds: list["Round"] = Relationship(back_populates="category")

    def has_organizer(self, user: User) -> bool:
        return self.tournament.has_organizer(user)


class CategoryCreate(CategoryBase):
    tournament_id: uuid.UUID


class CategoryPublic(CategoryBase):
    id: uuid.UUID
    tournament_id: uuid.UUID


class CategoryUpdate(SQLModel):
    name: str | None = None
