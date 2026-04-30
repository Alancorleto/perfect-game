import uuid
from datetime import date

from sqlmodel import Field, SQLModel


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
