import uuid
from sqlmodel import Field, SQLModel, Relationship
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from models.sum_format import SumFormat
    from models.score import Score


class SumFormatScoreLink(SQLModel, table=True):
    round_id: uuid.UUID = Field(foreign_key="sumformat.round_id", primary_key=True)
    score_id: uuid.UUID = Field(foreign_key="score.id", primary_key=True)

    format: "SumFormat" = Relationship(back_populates="score_links")
    score: "Score" = Relationship()
