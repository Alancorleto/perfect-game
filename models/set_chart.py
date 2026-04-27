import uuid
from sqlmodel import Field, SQLModel, Relationship
from typing import TYPE_CHECKING
from models.chart import Chart
from models.round import Round
from models.set import Set


class SetChartLink(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    set_id: uuid.UUID = Field(foreign_key="set.id")
    chart_id: uuid.UUID = Field(foreign_key="chart.id")
    order_index: int = Field(ge=0)

    set: Set = Relationship(back_populates="chart_links")
    chart: Chart = Relationship()
