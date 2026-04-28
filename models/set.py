import uuid
from sqlmodel import Field, SQLModel, Relationship
from models.round import Round
from typing import TYPE_CHECKING
from enum import Enum

if TYPE_CHECKING:
    from models.chart_slot import ChartSlot
    from models.set_player import SetPlayerLink


class SetFormat(Enum):
    SCORE_SUM = "score_sum"
    BATTLE = "battle"
    CUSTOM_SET = "custom_set"


class SetBase(SQLModel):
    levels: str | None = None
    qualifiers_count: int | None = Field(ge=1)
    format: SetFormat = Field(default=SetFormat.SCORE_SUM)


class Set(SetBase, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    round_id: uuid.UUID = Field(foreign_key="round.id")

    round: Round = Relationship(back_populates="sets")
    chart_slots: list["ChartSlot"] = Relationship(back_populates="set")
    player_links: list["SetPlayerLink"] = Relationship(back_populates="set")


class SetCreate(SetBase):
    round_id: uuid.UUID


class Result(SQLModel):
    player_id: uuid.UUID
    player_order_index: int
    set_id: uuid.UUID
    chart_order_index: int
    score_id: uuid.UUID | None = None
    score: int = 0
    place: int = -1
    is_tie: bool = False


class PlayerResults(SQLModel):
    player_id: uuid.UUID
    order_index: int
    results: list[Result] = []
    total_score: int = 0
