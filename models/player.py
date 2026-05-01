import uuid
from datetime import date
from typing import TYPE_CHECKING, Optional

from sqlmodel import Field, Relationship, SQLModel

from models.user import User

if TYPE_CHECKING:
    from models.tournament import Tournament


class PlayerBase(SQLModel):
    nickname: str
    name: str | None = None
    team_name: str | None = None
    birth_date: date | None = None
    country_code: str | None = None
    city: str | None = None
    profile_picture_url: str | None = None


class Player(PlayerBase, table=True):
    id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        primary_key=True,
    )
    user_id: uuid.UUID | None = Field(foreign_key="user.id", default=None)
    guest_tournament_id: uuid.UUID | None = Field(
        foreign_key="tournament.id", default=None
    )

    user: User | None = Relationship(back_populates="player")
    guest_tournament: Optional["Tournament"] = Relationship(
        back_populates="guest_players"
    )

    def can_be_edited_by(self, user: User) -> bool:
        return (
            self.user_id == user.id
            or (
                self.guest_tournament is not None
                and self.guest_tournament.can_be_edited_by(user)
            )
            or user.is_super_admin
        )


class PlayerCreate(PlayerBase):
    pass


class PlayerPublic(PlayerBase):
    id: uuid.UUID


class PlayerUpdate(SQLModel):
    nickname: str | None = None
    name: str | None = None
    team_name: str | None = None
    birth_date: date | None = None
    country_code: str | None = None
    city: str | None = None
    profile_picture_url: str | None = None
