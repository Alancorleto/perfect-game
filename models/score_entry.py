import uuid

from sqlmodel import Field, SQLModel


class ScoreEntry(SQLModel, table=True):
    chart_slot_id: uuid.UUID = Field(
        foreign_key="chartslot.id", primary_key=True, ondelete="CASCADE"
    )
    score_id: uuid.UUID = Field(
        foreign_key="score.id", primary_key=True, ondelete="CASCADE"
    )
