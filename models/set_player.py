import uuid
from typing import TYPE_CHECKING

from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from models.player import Player
    from models.set import Set


class SetPlayerLink(SQLModel, table=True):
    set_id: uuid.UUID = Field(
        foreign_key="set.id", primary_key=True, ondelete="CASCADE"
    )
    player_id: uuid.UUID = Field(
        foreign_key="player.id", primary_key=True, ondelete="CASCADE"
    )
    order_index: int = Field(ge=0)

    set: "Set" = Relationship(back_populates="player_links")
    player: "Player" = Relationship()
