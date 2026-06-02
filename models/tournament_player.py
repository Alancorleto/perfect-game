import uuid
from typing import TYPE_CHECKING

from sqlmodel import Field, SQLModel
from sqlmodel.main import Relationship

from models.player import Player

if TYPE_CHECKING:
    from models.category import Category


class CategoryPlayerLinkBase(SQLModel):
    has_paid_entry: bool = Field(default=False)


class CategoryPlayerLink(CategoryPlayerLinkBase, SQLModel, table=True):
    category_id: uuid.UUID = Field(
        foreign_key="category.id", primary_key=True, ondelete="CASCADE"
    )
    player_id: uuid.UUID = Field(
        foreign_key="player.id", primary_key=True, ondelete="CASCADE"
    )

    category: "Category" = Relationship(back_populates="player_links")
    player: Player = Relationship(back_populates="category_links")


class CategoryPlayerLinkCreate(CategoryPlayerLinkBase):
    pass


class CategoryPlayerLinkUpdate(SQLModel):
    has_paid_entry: bool | None = Field(default=None)


class PlayerInCategory(CategoryPlayerLinkBase):
    player: Player
