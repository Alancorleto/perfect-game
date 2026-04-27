import uuid
from sqlmodel import Field, SQLModel, Relationship
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from models.set import Set
    from models.player import Player


class SetPlayerLink(SQLModel, table=True):
    set_id: uuid.UUID = Field(foreign_key="set.id", primary_key=True)
    player_id: uuid.UUID = Field(foreign_key="player.id", primary_key=True)
    order_index: int = Field(ge=0)

    set: "Set" = Relationship(back_populates="player_links")
    player: "Player" = Relationship()
