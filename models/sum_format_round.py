import uuid
from sqlmodel import Field, SQLModel, Relationship
from models.round import Round
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from models.sum_format_chart import SumFormatChartLink
    from models.sum_format_score import SumFormatScore


class SumFormatRoundBase(SQLModel):
    levels: str | None = None
    qualifiers_count: int = Field(ge=1)


class SumFormatRound(SumFormatRoundBase, table=True):
    round_id: uuid.UUID = Field(
        primary_key=True,
        foreign_key="round.id"
    )
    round: Round = Relationship(back_populates="sum_format")

    chart_links: list["SumFormatChartLink"] = Relationship()


class SumFormatRoundCreate(SumFormatRoundBase):
    round_id: uuid.UUID
