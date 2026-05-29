import uuid
from typing import TYPE_CHECKING

from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from .chart import Chart
    from .chart_column import ChartColumn
    from .player import Player


class ChartColumnEntry(SQLModel, table=True):
    chart_column_id: uuid.UUID = Field(
        foreign_key="chartcolumn.id", primary_key=True, ondelete="CASCADE"
    )
    player_id: uuid.UUID = Field(
        foreign_key="player.id", primary_key=True, ondelete="CASCADE"
    )
    chart_id: uuid.UUID = Field(
        foreign_key="chart.id", primary_key=True, ondelete="CASCADE"
    )

    chart_column: "ChartColumn" = Relationship(back_populates="chart_entries")
    player: "Player" = Relationship()
    chart: "Chart" = Relationship()
