import uuid
from enum import Enum
from typing import TYPE_CHECKING

from pydantic import BaseModel
from sqlmodel import Field, Relationship, SQLModel

from models.chart import Chart
from models.round import Round
from models.user import User

if TYPE_CHECKING:
    from models.chart_slot import ChartSlot
    from models.set_player import SetPlayerLink


class SetFormat(Enum):
    SCORE_SUM = "score_sum"
    BATTLE = "battle"
    CUSTOM_SET = "custom_set"


class SetBase(SQLModel):
    levels: str | None = None
    qualifiers_count: int | None = Field(ge=1, default=None)
    format: SetFormat = Field(default=SetFormat.SCORE_SUM)


class Set(SetBase, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    round_id: uuid.UUID = Field(foreign_key="round.id", ondelete="CASCADE")

    round: Round = Relationship(back_populates="sets")
    chart_slots: list["ChartSlot"] = Relationship(
        back_populates="set", cascade_delete=True
    )
    player_links: list["SetPlayerLink"] = Relationship(
        back_populates="set", cascade_delete=True
    )
    charts: list[Chart] = Relationship(back_populates="set")

    def can_be_edited_by(self, user: User) -> bool:
        return self.round.can_be_edited_by(user)

    def can_be_deleted(self, user: User) -> bool:
        return self.can_be_edited_by(user) and (
            user.is_super_admin
            or all(chart_slot.can_be_deleted(user) for chart_slot in self.chart_slots)
        )


class SetCreate(SetBase):
    round_id: uuid.UUID


class SetUpdate(SetBase):
    levels: str | None = None
    qualifiers_count: int | None = Field(ge=1, default=1)
    format: SetFormat | None = Field(default=SetFormat.SCORE_SUM)


class SetPublic(BaseModel):
    id: uuid.UUID
    round_id: uuid.UUID


class Result(BaseModel):
    player_id: uuid.UUID
    player_order_index: int
    set_id: uuid.UUID
    chart_order_index: int
    score_id: uuid.UUID | None = None
    score: int = 0
    place: int = -1
    is_tie: bool = False


class PlayerResults(BaseModel):
    player_id: uuid.UUID
    order_index: int
    results: list[Result] = []
    total_score: int = 0
    place: int = -1
    is_tie: bool = False


class ChartResults(BaseModel):
    chart_slot_id: uuid.UUID
    results: list[Result] = []
