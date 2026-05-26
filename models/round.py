import uuid
from enum import Enum
from typing import TYPE_CHECKING

from sqlmodel import Field, Relationship, SQLModel

from models.category import Category
from models.player import Player
from models.user import User

if TYPE_CHECKING:
    from models.set import Set


class RoundState(Enum):
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    PAUSED = "paused"
    FINISHED = "finished"


class RoundBase(SQLModel):
    name: str | None = Field(default=None, max_length=50)
    levels: str | None = Field(default=None, max_length=30)
    state: RoundState = Field(default=RoundState.NOT_STARTED)
    order_index: int = Field(default=0)


class Round(RoundBase, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    category_id: uuid.UUID = Field(foreign_key="category.id", ondelete="CASCADE")

    category: Category = Relationship(back_populates="rounds")

    sets: list["Set"] = Relationship(back_populates="round", cascade_delete=True)

    def can_be_edited_by(self, user: User) -> bool:
        return self.category.can_be_edited_by(user)

    def can_be_deleted(self, user: User) -> bool:
        return self.can_be_edited_by(user) and self.state == RoundState.NOT_STARTED

    def get_qualifying_players(self) -> list[Player]:
        qualifying_players = []

        for db_set in self.get_sets_by_order():
            qualifying_players.extend(db_set.get_qualifying_players())

        return qualifying_players

    def get_sets_by_order(self) -> list["Set"]:
        return sorted(self.sets, key=lambda s: s.order_index)


class RoundCreate(RoundBase):
    category_id: uuid.UUID


class RoundPublic(RoundBase):
    id: uuid.UUID
    category_id: uuid.UUID


class RoundUpdate(SQLModel):
    name: str | None = None
    state: RoundState | None = None
