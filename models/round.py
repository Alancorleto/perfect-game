import uuid
from models.set_score import SetScoreLink
from sqlmodel import Field, SQLModel, Relationship
from models.category import Category
from models.set_player import SetPlayerLink
from enum import Enum
from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from models.set import Set


class RoundFormat(Enum):
    SCORE_SUM = "score_sum"
    BATTLE = "battle"


class RoundState(Enum):
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    PAUSED = "paused"
    FINISHED = "finished"


class RoundBase(SQLModel):
    name: str | None = None
    format: RoundFormat = Field(default=RoundFormat.SCORE_SUM)
    state: RoundState = Field(default=RoundState.NOT_STARTED)


class Round(RoundBase, table=True):
    id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        primary_key=True
    )
    category_id: uuid.UUID = Field(foreign_key="category.id")

    category: Category = Relationship(back_populates="rounds")
    player_links: list[SetPlayerLink] = Relationship(back_populates="round")
    score_links: list[SetScoreLink] = Relationship(back_populates="round")

    set: "Set" = Relationship(back_populates="round")
    # sets: list["Set"] = Relationship(back_populates="round")
    # battles: list["Battle"] = Relationship(back_populates="round")
    # custom_set: "CustomSet" = Relationship(back_populates="round")
    # heart_battles: list["HeartBattle"] = Relationship(back_populates="round")


class RoundCreate(RoundBase):
    category_id: uuid.UUID


class RoundPublic(RoundBase):
    id: uuid.UUID
    category_id: uuid.UUID


class RoundUpdate(SQLModel):
    name: str | None = None
    format: RoundFormat | None = None
    state: RoundState | None = None
