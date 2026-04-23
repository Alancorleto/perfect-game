import uuid
from sqlmodel import Field, SQLModel, Relationship
from models.round import Round
from models.sum_format_chart import SumFormatChartLink
from models.sum_format_score import SumFormatScoreLink


class SumFormatBase(SQLModel):
    levels: str | None = None
    qualifiers_count: int = Field(ge=1)


class SumFormat(SumFormatBase, table=True):
    round_id: uuid.UUID = Field(
        primary_key=True,
        foreign_key="round.id"
    )
    round: Round = Relationship(back_populates="sum_format")

    chart_links: list[SumFormatChartLink] = Relationship(back_populates="format")
    score_links: list[SumFormatScoreLink] = Relationship(back_populates="format")


class SumFormatCreate(SumFormatBase):
    round_id: uuid.UUID
