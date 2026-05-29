import uuid

from sqlmodel import Field, SQLModel


class ScoreColumnChartLink(SQLModel, table=True):
    score_column_id: uuid.UUID = Field(
        foreign_key="scorecolumn.id", primary_key=True, ondelete="CASCADE"
    )
    chart_id: uuid.UUID = Field(
        foreign_key="chart.id", primary_key=True, ondelete="CASCADE"
    )
