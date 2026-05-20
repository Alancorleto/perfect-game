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
    category_id: uuid.UUID = Field(foreign_key="category.id", ondelete="CASCADE")

    category: Category = Relationship(back_populates="rounds")

    sets: list["Set"] = Relationship(back_populates="round", cascade_delete=True)

    def can_be_edited_by(self, user: User) -> bool:
        return self.category.can_be_edited_by(user)

    def can_be_deleted(self, user: User) -> bool:
        return self.can_be_edited_by(user) and self.state == RoundState.NOT_STARTED


class RoundCreate(RoundBase):
    category_id: uuid.UUID


class RoundPublic(RoundBase):
    id: uuid.UUID
    category_id: uuid.UUID


class RoundUpdate(SQLModel):
    name: str | None = None
    state: RoundState | None = None
