import uuid
from datetime import date, time
from typing import TYPE_CHECKING

from sqlmodel import Field, Relationship, SQLModel

from models.tournament_organizer import TournamentOrganizer
from models.user import User

if TYPE_CHECKING:
    from models.category import Category
    from models.player import Player
    from models.user import User

NAME_MIN_LENGTH = 3
NAME_MAX_LENGTH = 100


class EventBase(SQLModel):
    name: str = Field(min_length=NAME_MIN_LENGTH, max_length=NAME_MAX_LENGTH)
    country_code: str = Field(min_length=2, max_length=2)
    description: str | None = None
    location: str | None = None
    start_date: date | None = None
    start_time: time | None = None
    logo_url: str | None = None


class Event(EventBase, table=True):
    id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        primary_key=True,
    )
    categories: list["Category"] = Relationship(
        back_populates="tournament", cascade_delete=True
    )
    organizers: list["User"] = Relationship(
        back_populates="tournaments", link_model=TournamentOrganizer
    )
    guest_players: list["Player"] = Relationship(
        back_populates="guest_tournament",
        cascade_delete=True,
    )

    def can_be_edited_by(self, user: "User") -> bool:
        return user in self.organizers or user.is_super_admin

    def can_be_deleted(self, user: User) -> bool:
        return self.can_be_edited_by(user) and all(
            category.can_be_deleted(user) for category in self.categories
        )

    def get_categories_by_name(self) -> list["Category"]:
        return sorted(self.categories, key=lambda c: c.name)


class EventCreate(EventBase):
    pass


class EventPublic(EventBase):
    id: uuid.UUID


class EventUpdate(SQLModel):
    name: str | None = Field(
        default=None, min_length=NAME_MIN_LENGTH, max_length=NAME_MAX_LENGTH
    )
    country_code: str | None = Field(default=None, min_length=2, max_length=2)
    description: str | None = Field(default=None)
    location: str | None = Field(default=None)
    start_date: date | None = Field(default=None)
    start_time: time | None = Field(default=None)
