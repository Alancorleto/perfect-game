import uuid
from sqlmodel import Field, SQLModel, Relationship
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from models.round import Round
    from models.score import Score


class RoundScoreLink(SQLModel, table=True):
    round_id: uuid.UUID = Field(foreign_key="round.id", primary_key=True)
    score_id: uuid.UUID = Field(foreign_key="score.id", primary_key=True)
    repeat_index: int = Field(ge=0)

    round: "Round" = Relationship()
    score: "Score" = Relationship()
