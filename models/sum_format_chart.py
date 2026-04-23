import uuid
from sqlmodel import Field, SQLModel, Relationship
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from models.sum_format import SumFormat
    from models.chart import Chart


class SumFormatChartLink(SQLModel, table=True):
    round_id: uuid.UUID = Field(foreign_key="sumformat.round_id", primary_key=True)
    chart_id: uuid.UUID = Field(foreign_key="chart.id", primary_key=True)
    order_index: int = Field(ge=0)

    format: "SumFormat" = Relationship(back_populates="chart_links")
    chart: "Chart" = Relationship()
