import uuid
from sqlmodel import Field, SQLModel, Relationship
from models.round import Round
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from models.set_chart import SetChartLink


class SetBase(SQLModel):
    levels: str | None = None
    qualifiers_count: int = Field(ge=1)


class Set(SetBase, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    round_id: uuid.UUID = Field(foreign_key="round.id")

    round: Round = Relationship(back_populates="set")
    chart_links: list["SetChartLink"] = Relationship(back_populates="set")


class SetCreate(SetBase):
    round_id: uuid.UUID
