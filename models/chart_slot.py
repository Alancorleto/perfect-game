import uuid
from sqlmodel import Field, SQLModel, Relationship
from typing import TYPE_CHECKING
from models.chart import Chart
from models.set import Set

if TYPE_CHECKING:
    from models.score_entry import ScoreEntry


class ChartSlot(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    set_id: uuid.UUID = Field(foreign_key="set.id")
    chart_id: uuid.UUID = Field(foreign_key="chart.id")
    order_index: int = Field(ge=0)

    set: Set = Relationship(back_populates="chart_slots")
    chart: Chart = Relationship()
    score_entries: list["ScoreEntry"] = Relationship(back_populates="chart_slot")
