import uuid
from datetime import date
from typing import TYPE_CHECKING

from sqlmodel import Field, Relationship, SQLModel

from models.tournament_organizer import TournamentOrganizer
from models.user import User

if TYPE_CHECKING:
    from models.category import Category
    from models.user import User


class TournamentBase(SQLModel):
    name: str
    location: str | None = None
    start_date: date | None = None


class Tournament(TournamentBase, table=True):
    id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        primary_key=True,
    )
    categories: list["Category"] = Relationship(back_populates="tournament")
    organizers: list["User"] = Relationship(
        back_populates="tournaments", link_model=TournamentOrganizer
    )

    def has_organizer(self, user: "User") -> bool:
        return user in self.organizers


class TournamentCreate(TournamentBase):
    pass


class TournamentPublic(TournamentBase):
    id: uuid.UUID


class TournamentUpdate(SQLModel):
    name: str | None = None
    location: str | None = None
    start_date: date | None = None
