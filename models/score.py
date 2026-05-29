import uuid
from enum import Enum

from sqlmodel import Field, Relationship, SQLModel

from models.player import Player, PlayerPublic
from models.score_column import ScoreColumn, ScoreColumnPublic
from models.user import User


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
    player_id: uuid.UUID = Field(foreign_key="player.id", ondelete="CASCADE")
    score_column_id: uuid.UUID = Field(foreign_key="scorecolumn.id", ondelete="CASCADE")

    player: Player = Relationship(back_populates="scores")
    score_column: ScoreColumn = Relationship(back_populates="scores")

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
    grade: Grade | None = None
    stage_pass: bool | None = None
    video_url: str | None = None
