import uuid
from sqlmodel import Field, SQLModel, Relationship
from typing import TYPE_CHECKING
from models.chart import Chart
from models.round import Round
from models.set import Set


class SetChartLink(SQLModel, table=True):
    set_id: uuid.UUID = Field(foreign_key="set.id", primary_key=True)
    order_index: int = Field(ge=0, primary_key=True)
    chart_id: uuid.UUID = Field(foreign_key="chart.id")

    set: Set = Relationship(back_populates="chart_links")
    chart: Chart = Relationship()
