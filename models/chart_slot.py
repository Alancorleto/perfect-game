import uuid
from typing import TYPE_CHECKING

from sqlmodel import Field, Relationship, SQLModel

from models.chart import Chart, ChartPublic
from models.round import RoundState
from models.set import Set
from models.user import User

if TYPE_CHECKING:
    from models.score import Score


class ChartSlot(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    set_id: uuid.UUID = Field(foreign_key="set.id", ondelete="CASCADE")
    chart_id: uuid.UUID | None = Field(foreign_key="chart.id", ondelete="SET NULL")
    order_index: int = Field(ge=0, default=0)
    description: str | None = Field(default=None, max_length=20)

    set: Set = Relationship(back_populates="chart_slots")
    chart: Chart | None = Relationship()
    scores: list["Score"] = Relationship(
        back_populates="chart_slot", cascade_delete=True
    )

    def can_be_edited_by(self, user: User) -> bool:
        return self.set.can_be_edited_by(user)

    def can_be_deleted(self, user: User) -> bool:
        return user.is_super_admin or (
            self.can_be_edited_by(user) and self.set.round.state != RoundState.FINISHED
        )


class ChartSlotCreate(SQLModel):
    set_id: uuid.UUID
    chart_id: uuid.UUID | None = None
    description: str | None = Field(default=None, max_length=20)


class ChartSlotUpdate(SQLModel):
    chart_id: uuid.UUID | None = None
    description: str | None = Field(default=None, max_length=20)


class ChartSlotPublic(SQLModel):
    id: uuid.UUID
    set_id: uuid.UUID
    chart_id: uuid.UUID | None
    order_index: int
    description: str | None

    chart: ChartPublic | None = None
