from sqlmodel import Relationship, SQLModel, Field
from enum import Enum
from models.round import Round
from models.player import Player
from models.chart import Chart
import uuid


class Grade(Enum):
    F = "F"
    D = "D"
    C = "C"
    B = "B"
    A = "A"
    A_P = "A+"
    AA = "AA"
    AA_P = "AA+"
    AAA = "AAA"
    AAA_P = "AAA+"
    S = "S"
    S_P = "S+"
    SS = "SS"
    SS_P = "SS+"
    SSS = "SSS"
    SSS_P = "SSS+"


class ScoreBase(SQLModel):
    value: int = Field(ge=0)
    perfect: int = Field(ge=0)
    great: int = Field(ge=0)
    good: int = Field(ge=0)
    bad: int = Field(ge=0)
    miss: int = Field(ge=0)
    max_combo: int = Field(ge=0)
    kcal: float = Field(ge=0)
    grade: Grade = Field(default=Grade.S)
    stage_pass: bool = True
    video_url: str | None = None


class Score(ScoreBase, table=True):
    id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        primary_key=True,
    )
    player_id: uuid.UUID = Field(foreign_key="player.id")
    chart_id: uuid.UUID = Field(foreign_key="chart.id")

    player: Player = Relationship()
    chart: Chart = Relationship()


class ScoreCreate(ScoreBase):
    player_id: uuid.UUID
    chart_id: uuid.UUID
    round_id: uuid.UUID | None = None
    repeat_index: int | None = None


class ScorePublic(ScoreBase):
    id: uuid.UUID
    player_id: uuid.UUID
    chart_id: uuid.UUID


class ScoreUpdate(SQLModel):
    value: int | None = Field(ge=0, default = None)
    perfect: int | None = Field(ge=0, default = None)
    great: int | None = Field(ge=0, default = None)
    good: int | None = Field(ge=0, default = None)
    bad: int | None = Field(ge=0, default = None)
    miss: int | None = Field(ge=0, default = None)
    max_combo: int | None = Field(ge=0, default = None)
    kcal: float | None = Field(ge=0, default = None)
    grade: Grade | None = None
    stage_pass: bool | None = None
    video_url: str | None = None
