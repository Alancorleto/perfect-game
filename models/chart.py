import uuid
from enum import Enum
from typing import TYPE_CHECKING

from sqlmodel import Field, Relationship, SQLModel

from models.song import Song, SongPublic
from models.user import User

if TYPE_CHECKING:
    from models.score import Score


class Mode(Enum):
    SINGLE = "single"
    DOUBLE = "double"
    SINGLE_PERFORMANCE = "single_performance"
    DOUBLE_PERFORMANCE = "double_performance"
    HALF_DOUBLE = "half_double"
    COOP = "coop"


class ChartBase(SQLModel):
    mode: Mode = Field(default=Mode.SINGLE)
    level: int = Field(ge=1, default=1)
    player_count: int = Field(ge=1, default=1)


class Chart(ChartBase, table=True):
    id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        primary_key=True,
    )
    song_id: uuid.UUID = Field(foreign_key="song.id", ondelete="CASCADE")

    song: Song = Relationship(back_populates="charts")

    # This is not used but needed by SQLModel to work properly with cascade delete
    scores: list["Score"] = Relationship(back_populates="chart", cascade_delete=True)

    def can_be_deleted(self, user: User) -> bool:
        return user.is_super_admin


class ChartCreate(ChartBase):
    song_id: uuid.UUID


class ChartPublic(ChartBase):
    id: uuid.UUID
    song: SongPublic


class ChartUpdate(SQLModel):
    mode: Mode | None = None
    level: int | None = None
    player_count: int | None = None
