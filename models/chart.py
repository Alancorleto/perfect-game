import uuid
from enum import Enum
from typing import TYPE_CHECKING

from sqlmodel import Field, Relationship, SQLModel

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
    creator_id: uuid.UUID = Field(foreign_key="user.id")

    creator: User = Relationship()

    # This is not used but needed by SQLModel to work properly with cascade delete
    scores: list["Score"] = Relationship(back_populates="chart", cascade_delete=True)

    def can_be_edited_by(self, user: User) -> bool:
        return user.is_super_admin or user == self.creator

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
