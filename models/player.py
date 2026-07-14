import uuid
from datetime import date
from typing import TYPE_CHECKING, Optional

from sqlmodel import Field, Relationship, SQLModel

from models.user import User

if TYPE_CHECKING:
    from models.event import Event
    from models.score import Score
    from models.tournament import TournamentInvitation, TournamentJoinRequest
    from models.tournament_player import TournamentPlayerLink

NICKNAME_MAX_LENGTH = 30
NAME_MAX_LENGTH = 50
TEAM_NAME_MAX_LENGTH = 50
CITY_MAX_LENGTH = 50


class PlayerBase(SQLModel):
    nickname: str = Field(max_length=NICKNAME_MAX_LENGTH)
    country_code: str = Field(min_length=2, max_length=2)
    name: str | None = Field(default=None, max_length=NAME_MAX_LENGTH)
    team_name: str | None = Field(default=None, max_length=TEAM_NAME_MAX_LENGTH)
    birth_date: date | None = Field(default=None)
    city: str | None = Field(default=None, max_length=CITY_MAX_LENGTH)
    profile_picture_url: str | None = Field(default=None)


class Player(PlayerBase, table=True):
    id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        primary_key=True,
    )
    user_id: uuid.UUID | None = Field(
        foreign_key="user.id", default=None, ondelete="SET NULL"
    )
    guest_event_id: uuid.UUID | None = Field(
        foreign_key="event.id", default=None, ondelete="CASCADE"
    )

    user: User | None = Relationship(back_populates="player")
    guest_event: Optional["Event"] = Relationship(back_populates="guest_players")

    # This is not used but needed by SQLModel to work properly with cascade delete
    scores: list["Score"] = Relationship(back_populates="player", cascade_delete=True)

    tournament_invitations: list["TournamentInvitation"] = Relationship(
        back_populates="player", cascade_delete=True
    )
    tournament_join_requests: list["TournamentJoinRequest"] = Relationship(
        back_populates="player", cascade_delete=True
    )
    tournament_links: list["TournamentPlayerLink"] = Relationship(
        back_populates="player", cascade_delete=True
    )

    def can_be_edited_by(self, user: User) -> bool:
        return (
            self.user_id == user.id
            or (
                self.guest_event is not None and self.guest_event.can_be_edited_by(user)
            )
            or user.is_super_admin
        )

    def can_be_deleted(self, user: User) -> bool:
        return user.is_super_admin


class PlayerCreate(PlayerBase):
    pass


class PlayerPublic(PlayerBase):
    id: uuid.UUID
    user_id: uuid.UUID | None
    guest_event_id: uuid.UUID | None


class PlayerUpdate(SQLModel):
    nickname: str | None = Field(default=None, max_length=NICKNAME_MAX_LENGTH)
    country_code: str | None = Field(default=None, min_length=2, max_length=2)
    name: str | None = Field(default=None, max_length=NAME_MAX_LENGTH)
    team_name: str | None = Field(default=None, max_length=TEAM_NAME_MAX_LENGTH)
    birth_date: date | None = Field(default=None)
    city: str | None = Field(default=None, max_length=CITY_MAX_LENGTH)
