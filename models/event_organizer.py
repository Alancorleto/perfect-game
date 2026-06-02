import uuid

from sqlmodel import Field, SQLModel


class EventOrganizer(SQLModel, table=True):
    event_id: uuid.UUID = Field(
        primary_key=True, foreign_key="event.id", ondelete="CASCADE"
    )
    user_id: uuid.UUID = Field(
        primary_key=True, foreign_key="user.id", ondelete="CASCADE"
    )
