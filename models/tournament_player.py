import uuid
from typing import TYPE_CHECKING

from sqlmodel import Field, SQLModel
from sqlmodel.main import Relationship

from models.player import Player

if TYPE_CHECKING:
    from models.tournament import Tournament


class TournamentPlayerLinkBase(SQLModel):
    has_paid_entry: bool = Field(default=False)


class TournamentPlayerLink(TournamentPlayerLinkBase, SQLModel, table=True):
    tournament_id: uuid.UUID = Field(
        foreign_key="tournament.id", primary_key=True, ondelete="CASCADE"
    )
    player_id: uuid.UUID = Field(
        foreign_key="player.id", primary_key=True, ondelete="CASCADE"
    )

    tournament: "Tournament" = Relationship(back_populates="player_links")
    player: Player = Relationship(back_populates="tournament_links")


class TournamentPlayerLinkCreate(TournamentPlayerLinkBase):
    pass


class TournamentPlayerLinkUpdate(SQLModel):
    has_paid_entry: bool | None = Field(default=None)


class PlayerInTournament(TournamentPlayerLinkBase):
    player: Player
