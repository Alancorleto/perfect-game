import uuid
from models.set_score import SetScoreLink
from sqlmodel import Field, SQLModel, Relationship
from models.category import Category
from models.set_player import SetPlayerLink
from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from models.set import Set


class RoundState(Enum):
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    PAUSED = "paused"
    FINISHED = "finished"


class RoundBase(SQLModel):
    name: str | None = None
    state: RoundState = Field(default=RoundState.NOT_STARTED)


class Round(RoundBase, table=True):
    id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        primary_key=True
    )
    category_id: uuid.UUID = Field(foreign_key="category.id")

    category: Category = Relationship(back_populates="rounds")

    sets: list["Set"] = Relationship(back_populates="round")


class RoundCreate(RoundBase):
    category_id: uuid.UUID


class RoundPublic(RoundBase):
    id: uuid.UUID
    category_id: uuid.UUID


class RoundUpdate(SQLModel):
    name: str | None = None
    state: RoundState | None = None
