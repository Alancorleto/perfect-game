import uuid
from datetime import date

from sqlmodel import Field, SQLModel

NICKNAME_MAX_LENGTH = 30
NAME_MAX_LENGTH = 50
TEAM_NAME_MAX_LENGTH = 50
CITY_MAX_LENGTH = 50


class PlayerPublic(SQLModel):
    id: uuid.UUID
    nickname: str
    country_code: str
    name: str | None = None
    team_name: str | None = None
    birth_date: date | None = None
    city: str | None = None
    profile_picture_url: str | None = None
    user_id: uuid.UUID | None = None
    guest_tournament_id: uuid.UUID | None = None


class PlayerUpdate(SQLModel):
    nickname: str | None = Field(default=None, max_length=NICKNAME_MAX_LENGTH)
    country_code: str | None = Field(default=None, min_length=2, max_length=2)
    name: str | None = Field(default=None, max_length=NAME_MAX_LENGTH)
    team_name: str | None = Field(default=None, max_length=TEAM_NAME_MAX_LENGTH)
    birth_date: date | None = Field(default=None)
    city: str | None = Field(default=None, max_length=CITY_MAX_LENGTH)
    profile_picture_url: str | None = None
