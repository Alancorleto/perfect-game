import uuid
from typing import TYPE_CHECKING

from sqlmodel import Field, Relationship, SQLModel

from models.chart import Chart
from models.score_entry import ScoreEntry
from models.set import Set

if TYPE_CHECKING:
    from models.score import Score


class ChartSlot(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    set_id: uuid.UUID = Field(foreign_key="set.id")
    chart_id: uuid.UUID = Field(foreign_key="chart.id")
    order_index: int = Field(ge=0)

    set: Set = Relationship(back_populates="chart_slots")
    chart: Chart = Relationship()
    score_entries: list[ScoreEntry] = Relationship(back_populates="chart_slot")
    scores: list["Score"] = Relationship(link_model=ScoreEntry)
