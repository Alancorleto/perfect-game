import uuid
from typing import TYPE_CHECKING

from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from models.player import Player
    from models.score_table import ScoreTable


class ScoreTablePlayerLink(SQLModel, table=True):
    score_table_id: uuid.UUID = Field(
        foreign_key="score_table.id", primary_key=True, ondelete="CASCADE"
    )
    player_id: uuid.UUID = Field(
        foreign_key="player.id", primary_key=True, ondelete="CASCADE"
    )
    order_index: int = Field(ge=0)

    score_table: "ScoreTable" = Relationship(back_populates="player_links")
    player: "Player" = Relationship()
