import uuid
from typing import TYPE_CHECKING

from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from models.chart_slot import ChartSlot
    from models.score import Score


class ScoreEntry(SQLModel, table=True):
    chart_slot_id: uuid.UUID = Field(foreign_key="chartslot.id", primary_key=True)
    score_id: uuid.UUID = Field(foreign_key="score.id", primary_key=True)

    chart_slot: "ChartSlot" = Relationship()
    score: "Score" = Relationship()
