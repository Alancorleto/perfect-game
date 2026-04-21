import uuid
from sqlmodel import Field, SQLModel, Relationship
from models.player import Player
from models.category import Category
from models.category_player import CategoryPlayerLink
from models.round_player import RoundPlayerLink
from enum import Enum

class RoundFormat(Enum):
    SCORE_SUM = "score_sum"
    BATTLE = "battle"


class RoundState(Enum):
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    PAUSED = "paused"
    COMPLETED = "completed"


class RoundBase(SQLModel):
    name: str | None = None
    format: RoundFormat = Field(default=RoundFormat.SCORE_SUM)
    levels: str | None = None
    qualifiers_count: int = Field(ge=1)
    state: RoundState = Field(default=RoundState.NOT_STARTED)


class Round(RoundBase, table=True):
    id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        primary_key=True
    )
    category_id: uuid.UUID = Field(foreign_key="category.id")
    
    category: Category = Relationship(back_populates="rounds")
    player_links: list[RoundPlayerLink] = Relationship(back_populates="round")


class RoundCreate(RoundBase):
    pass


class RoundPublic(RoundBase):
    id: uuid.UUID
    category_id: uuid.UUID
