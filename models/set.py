import uuid
from sqlmodel import Field, SQLModel, Relationship
from models.round import Round
from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from models.set_chart import SetChartLink
    from models.score import Score


class SetBase(SQLModel):
    levels: str | None = None
    qualifiers_count: int = Field(ge=1)


class Set(SetBase, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    round_id: uuid.UUID = Field(foreign_key="round.id")

    round: Round = Relationship(back_populates="set")
    chart_links: list["SetChartLink"] = Relationship(back_populates="set")


class SetCreate(SetBase):
    round_id: uuid.UUID


class SetResultScore(SQLModel):
    chart_id: uuid.UUID
    repeat_index: int
    score: int
    score_id: uuid.UUID | None = None


class SetResult(SQLModel):
    player_id: uuid.UUID
    order_index: int
    scores: list[SetResultScore] # chart_id to score
    total_score: int
