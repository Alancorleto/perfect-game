import uuid

from pydantic import BaseModel
from sqlmodel import Field, Relationship, SQLModel

from models.chart import Chart
from models.player import Player, PlayerPublic
from models.score_column import ScoreColumn, ScoreColumnPublic
from models.score_grade import ScoreGrade
from models.user import User


class ScoreBase(SQLModel):
    value: int = Field(ge=0)
    perfect: int = Field(ge=0)
    great: int = Field(ge=0)
    good: int = Field(ge=0)
    bad: int = Field(ge=0)
    miss: int = Field(ge=0)
    max_combo: int = Field(ge=0)
    kcal: float = Field(ge=0)
    grade: ScoreGrade = Field(default=ScoreGrade.S)
    stage_pass: bool = True
    video_url: str | None = None


class Score(ScoreBase, table=True):
    id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        primary_key=True,
    )
    player_id: uuid.UUID = Field(foreign_key="player.id", ondelete="CASCADE")
    score_column_id: uuid.UUID = Field(foreign_key="scorecolumn.id", ondelete="CASCADE")
    chart_id: uuid.UUID | None = Field(foreign_key="chart.id", default=None, ondelete="SET NULL")

    player: Player = Relationship(back_populates="scores")
    score_column: ScoreColumn = Relationship(back_populates="scores")
    chart: Chart | None = Relationship(back_populates="score")


    def can_be_edited_by(self, user: User) -> bool:
        return (
            self.score_column is not None
            and self.score_column.score_table.can_be_edited_by(user)
        )

    def can_be_deleted(self, user: User) -> bool:
        return user.is_super_admin


class ScoreCreate(ScoreBase):
    player_id: uuid.UUID
    score_column_id: uuid.UUID


class ScorePublic(ScoreBase):
    id: uuid.UUID

    player: PlayerPublic
    score_column: ScoreColumnPublic


class ScoreUpdate(SQLModel):
    value: int | None = Field(ge=0, default=None)
    perfect: int | None = Field(ge=0, default=None)
    great: int | None = Field(ge=0, default=None)
    good: int | None = Field(ge=0, default=None)
    bad: int | None = Field(ge=0, default=None)
    miss: int | None = Field(ge=0, default=None)
    max_combo: int | None = Field(ge=0, default=None)
    kcal: float | None = Field(ge=0, default=None)
    grade: ScoreGrade | None = None
    stage_pass: bool | None = None
    video_url: str | None = None


class ListScoresResponse(BaseModel):
    scores: list[ScorePublic]
    offset: int
    size: int
    total_count: int
