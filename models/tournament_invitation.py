import datetime
import uuid
from enum import Enum

from sqlmodel import Field, Relationship, SQLModel

from models.player import Player
from models.tournament import Tournament


class RequestStatus(Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    DECLINED = "declined"


class TournamentRequestBase(SQLModel):
    status: RequestStatus = Field(default=RequestStatus.PENDING)
    issued_at: datetime.datetime = Field(default_factory=datetime.datetime.now)


class TournamentInvitation(TournamentRequestBase, table=True):
    tournament_id: uuid.UUID = Field(
        primary_key=True, foreign_key="tournament.id", ondelete="CASCADE"
    )
    player_id: uuid.UUID = Field(
        primary_key=True, foreign_key="player.id", ondelete="CASCADE"
    )

    tournament: Tournament = Relationship(back_populates="invitations")
    player: Player = Relationship(back_populates="tournament_invitations")


class TournamentInvitationPublic(SQLModel):
    tournament_id: uuid.UUID
    player: Player
    status: RequestStatus = Field(default=RequestStatus.PENDING)


class TournamentJoinRequest(TournamentRequestBase, table=True):
    tournament_id: uuid.UUID = Field(
        primary_key=True, foreign_key="tournament.id", ondelete="CASCADE"
    )
    player_id: uuid.UUID = Field(
        primary_key=True, foreign_key="player.id", ondelete="CASCADE"
    )

    tournament: Tournament = Relationship(back_populates="join_requests")
    player: Player = Relationship(back_populates="tournament_join_requests")


class TournamentJoinRequestPublic(TournamentRequestBase):
    player_id: uuid.UUID
    tournament: Tournament
    status: RequestStatus = Field(default=RequestStatus.PENDING)
