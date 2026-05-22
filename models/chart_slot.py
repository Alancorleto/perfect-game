import uuid
from typing import TYPE_CHECKING

from sqlmodel import Field, Relationship, SQLModel

from models.chart import Chart
from models.score_entry import ScoreEntry
from models.set import Set
from models.user import User

if TYPE_CHECKING:
    from models.score import Score


class ChartSlot(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    set_id: uuid.UUID = Field(foreign_key="set.id", ondelete="CASCADE")
    chart_id: uuid.UUID | None = Field(foreign_key="chart.id", ondelete="SET NULL")
    order_index: int = Field(ge=0)

    set: Set = Relationship(back_populates="chart_slots")
    chart: Chart | None = Relationship()
    scores: list["Score"] = Relationship(
        link_model=ScoreEntry, back_populates="chart_slot"
    )

    def can_be_edited_by(self, user: User) -> bool:
        return self.set.can_be_edited_by(user)

    def can_be_deleted(self, user: User) -> bool:
        return user.is_super_admin or len(self.scores) == 0


class ChartSlotPublic(SQLModel):
    id: uuid.UUID
    set_id: uuid.UUID
    chart_id: uuid.UUID | None
    order_index: int
