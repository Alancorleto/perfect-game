import uuid
from datetime import date
from typing import TYPE_CHECKING

from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from models.tournament import Tournament
    from models.user import User


class TournamentOrganizer(SQLModel, table=True):
    tournament_id: uuid.UUID = Field(foreign_key="tournament.id")
    user_id: uuid.UUID = Field(foreign_key="user.id")

    tournament: "Tournament" = Relationship(back_populates="organizers")
    user: "User" = Relationship(back_populates="tournaments")
