import uuid
from typing import TYPE_CHECKING

from sqlmodel import Field, SQLModel
from sqlmodel.main import Relationship

if TYPE_CHECKING:
    from models.category import Category
    from models.player import Player


class CategoryPlayerLink(SQLModel, table=True):
    category_id: uuid.UUID = Field(
        foreign_key="category.id", primary_key=True, ondelete="CASCADE"
    )
    player_id: uuid.UUID = Field(
        foreign_key="player.id", primary_key=True, ondelete="CASCADE"
    )
    has_paid_entry: bool = Field(default=False)

    category: "Category" = Relationship(back_populates="player_links")
    player: "Player" = Relationship(back_populates="category_links")
