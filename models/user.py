import uuid
from typing import TYPE_CHECKING, Optional

from pydantic import EmailStr
from sqlmodel import Field, Relationship, SQLModel

from models.tournament_organizer import TournamentOrganizer

if TYPE_CHECKING:
    from models.player import Player
    from models.tournament import Tournament


class Token(SQLModel):
    access_token: str
    token_type: str


class TokenData(SQLModel):
    username: str | None = None


class UserBase(SQLModel):
    email: EmailStr | None = None


class User(UserBase, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    hashed_password: str
    is_super_admin: bool = False

    tournaments: list["Tournament"] = Relationship(
        back_populates="organizers", link_model=TournamentOrganizer
    )
    player: Optional["Player"] = Relationship(back_populates="user")


class UserPublic(UserBase):
    id: uuid.UUID


class UserCreate(UserBase):
    password: str = Field(min_length=8, max_length=100)


class UserUpdate(SQLModel):
    password: str | None = Field(min_length=8, max_length=100, default=None)
    email: EmailStr | None = Field(default=None)
