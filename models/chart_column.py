import uuid

from sqlmodel import Field, Relationship, SQLModel

from models.chart_column_entry import ChartColumnEntry
from models.round import RoundState
from models.score_column import ScoreColumn
from models.user import User


class ChartColumn(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    score_column_id: uuid.UUID = Field(foreign_key="scorecolumn.id", ondelete="CASCADE")
    description: str | None = Field(default=None, max_length=20)

    score_column: ScoreColumn = Relationship(back_populates="chart_column")
    chart_entries: list[ChartColumnEntry] = Relationship(back_populates="chart_column")

    def can_be_edited_by(self, user: User) -> bool:
        return self.score_column.can_be_edited_by(user)

    def can_be_deleted(self, user: User) -> bool:
        return user.is_super_admin or (
            self.can_be_edited_by(user)
            and self.score_column.score_table.round.state != RoundState.FINISHED
        )


class ChartColumnCreate(SQLModel):
    score_column_id: uuid.UUID
    description: str | None = Field(default=None, max_length=20)


class ChartColumnUpdate(SQLModel):
    description: str | None = Field(default=None, max_length=20)


class ChartColumnPublic(SQLModel):
    id: uuid.UUID
    score_column_id: uuid.UUID
    description: str | None
