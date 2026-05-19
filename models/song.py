import uuid
from typing import TYPE_CHECKING

from sqlmodel import Field, Relationship, SQLModel

from models.user import User

if TYPE_CHECKING:
    from models.chart import Chart


class SongBase(SQLModel):
    name: str
    title_url: str | None = None


class Song(SongBase, table=True):
    id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        primary_key=True,
    )

    # This is not used but needed by SQLModel to work properly with cascade delete
    charts: list["Chart"] = Relationship(back_populates="song", cascade_delete=True)

    def can_be_deleted(self, user: User) -> bool:
        return user.is_super_admin


class SongCreate(SongBase):
    pass


class SongPublic(SongBase):
    id: uuid.UUID


class SongUpdate(SQLModel):
    name: str | None = None
    title_url: str | None = None
