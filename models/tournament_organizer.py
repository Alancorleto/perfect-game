import uuid
from typing import TYPE_CHECKING

from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from models.tournament import Tournament
    from models.user import User


class TournamentOrganizer(SQLModel, table=True):
    tournament_id: uuid.UUID = Field(primary_key=True, foreign_key="tournament.id")
    user_id: uuid.UUID = Field(primary_key=True, foreign_key="user.id")
