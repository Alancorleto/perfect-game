import uuid
from enum import Enum
from typing import TYPE_CHECKING, Optional

from sqlmodel import Field, Relationship, SQLModel

from models.score_column_chart import ScoreColumnChartLink
from models.user import User

if TYPE_CHECKING:
    from models.score_column import ScoreColumn


class Mode(Enum):
    SINGLE = "single"
    DOUBLE = "double"
    SINGLE_PERFORMANCE = "single_performance"
    DOUBLE_PERFORMANCE = "double_performance"
    HALF_DOUBLE = "half_double"
    COOP = "coop"


class ChartBase(SQLModel):
    song_name: str = Field(min_length=1)
    mode: Mode = Field(default=Mode.SINGLE)
    level: int = Field(ge=1, default=1)
    player_count: int = Field(ge=1, default=1)
    title_url: str | None = Field(default=None)


class Chart(ChartBase, table=True):
    id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        primary_key=True,
    )

    score_column: Optional["ScoreColumn"] = Relationship(
        link_model=ScoreColumnChartLink
    )

    def can_be_edited_by(self, user: User) -> bool:
        return user.is_super_admin or (
            self.score_column is not None and self.score_column.can_be_edited_by(user)
        )

    def can_be_deleted(self, user: User) -> bool:
        return user.is_super_admin


class ChartCreate(ChartBase):
    pass


class ChartPublic(ChartBase):
    id: uuid.UUID


class ChartUpdate(SQLModel):
    song_name: str | None = Field(min_length=1, default=None)
    mode: Mode | None = Field(default=None)
    level: int | None = Field(ge=1, default=None)
    player_count: int | None = Field(ge=1, default=None)
    title_url: str | None = Field(default=None)
