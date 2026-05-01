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
    is_super_admin: bool = False


class User(UserBase, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    hashed_password: str

    tournaments: list["Tournament"] = Relationship(
        back_populates="organizers", link_model=TournamentOrganizer
    )
    player: Optional["Player"] = Relationship(back_populates="user")


class UserPublic(UserBase):
    id: uuid.UUID


class UserCreate(UserBase):
    password: str
