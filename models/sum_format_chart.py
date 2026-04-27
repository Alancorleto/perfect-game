import uuid
from sqlmodel import Field, SQLModel, Relationship
from typing import TYPE_CHECKING
from models.chart import Chart
from models.round import Round


class SumFormatChartLink(SQLModel, table=True):
    round_id: uuid.UUID = Field(foreign_key="round.id", primary_key=True)
    chart_id: uuid.UUID = Field(foreign_key="chart.id", primary_key=True)
    repeat_index: int = Field(ge=0)
    order_index: int = Field(ge=0)

    round: Round = Relationship()
    chart: Chart = Relationship()
