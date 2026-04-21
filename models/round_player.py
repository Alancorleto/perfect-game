import uuid
from sqlmodel import Field, SQLModel, Relationship
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from models.round import Round


class RoundPlayerLink(SQLModel, table=True):
    round_id: uuid.UUID = Field(foreign_key="round.id", primary_key=True)
    player_id: uuid.UUID = Field(foreign_key="player.id", primary_key=True)
    order_index: int = Field(ge=0)

    round: "Round" = Relationship(back_populates="player_links")
