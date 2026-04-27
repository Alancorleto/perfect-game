import uuid
from sqlmodel import Field, SQLModel, Relationship
from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from models.set import Set
    from models.score import Score
    from models.set_chart import SetChartLink


class SetScoreLink(SQLModel, table=True):
    set_id: uuid.UUID = Field(foreign_key="set.id", primary_key=True)
    score_id: uuid.UUID = Field(foreign_key="score.id", primary_key=True)
    order_index: int = Field(ge=0)

    set: "Set" = Relationship()
    score: "Score" = Relationship()
    
