import uuid

from sqlmodel import Field, SQLModel


class TournamentOrganizer(SQLModel, table=True):
    tournament_id: uuid.UUID = Field(
        primary_key=True, foreign_key="tournament.id", ondelete="CASCADE"
    )
    user_id: uuid.UUID = Field(
        primary_key=True, foreign_key="user.id", ondelete="CASCADE"
    )
