import uuid
from enum import Enum
from typing import TYPE_CHECKING

from sqlmodel import Field, Relationship, SQLModel

from models.category import Category
from models.user import User

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
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    category_id: uuid.UUID = Field(foreign_key="category.id")

    category: Category = Relationship(back_populates="rounds")

    sets: list["Set"] = Relationship(back_populates="round")

    def has_organizer(self, user: User) -> bool:
        return user in self.category.tournament.organizers


class RoundCreate(RoundBase):
    category_id: uuid.UUID


class RoundPublic(RoundBase):
    id: uuid.UUID
    category_id: uuid.UUID


class RoundUpdate(SQLModel):
    name: str | None = None
    state: RoundState | None = None
