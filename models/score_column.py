import uuid
from typing import TYPE_CHECKING

from sqlmodel import Field, Relationship, SQLModel

from models.chart import Chart, ChartPublic
from models.round import RoundState
from models.score_table import ScoreTable
from models.user import User

if TYPE_CHECKING:
    from models.score import Score


class ScoreColumn(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    score_table_id: uuid.UUID = Field(foreign_key="scoretable.id", ondelete="CASCADE")
    chart_id: uuid.UUID | None = Field(foreign_key="chart.id", ondelete="SET NULL")
    order_index: int = Field(ge=0, default=0)
    description: str | None = Field(default=None, max_length=20)

    score_table: ScoreTable = Relationship(back_populates="chart_slots")
    chart: Chart | None = Relationship()
    scores: list["Score"] = Relationship(
        back_populates="chart_slot", cascade_delete=True
    )

    def can_be_edited_by(self, user: User) -> bool:
        return self.score_table.can_be_edited_by(user)

    def can_be_deleted(self, user: User) -> bool:
        return user.is_super_admin or (
            self.can_be_edited_by(user)
            and self.score_table.round.state != RoundState.FINISHED
        )


class ScoreColumnCreate(SQLModel):
    score_table_id: uuid.UUID
    chart_id: uuid.UUID | None = None
    description: str | None = Field(default=None, max_length=20)


class ScoreColumnUpdate(SQLModel):
    chart_id: uuid.UUID | None = None
    description: str | None = Field(default=None, max_length=20)


class ScoreColumnPublic(SQLModel):
    id: uuid.UUID
    score_table_id: uuid.UUID
    chart_id: uuid.UUID | None
    order_index: int
    description: str | None

    chart: ChartPublic | None = None
