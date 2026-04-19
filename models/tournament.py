import uuid
from datetime import date
from sqlmodel import Field, SQLModel, Relationship


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


class TournamentCreate(TournamentBase):
    pass


class TournamentPublic(TournamentBase):
    id: uuid.UUID


class TournamentUpdate(SQLModel):
    name: str | None = None
    location: str | None = None
    start_date: date | None = None