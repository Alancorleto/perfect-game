from sqlmodel import SQLModel, Field
import uuid


class SongBase(SQLModel):
    name: str
    title_url: str | None = None


class Song(SongBase, table=True):
    id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        primary_key=True,
    )


class SongCreate(SongBase):
    pass


class SongPublic(SongBase):
    id: uuid.UUID


class SongUpdate(SQLModel):
    name: str | None = None
    title_url: str | None = None
