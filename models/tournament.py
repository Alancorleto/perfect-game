import uuid
from typing import TYPE_CHECKING

from sqlmodel import Field, Relationship, SQLModel

from models.event import Event
from models.player import Player
from models.tournament_player import TournamentPlayerLink
from models.user import User

if TYPE_CHECKING:
    from models.round import Round
    from models.tournament_invitation import TournamentInvitation, TournamentJoinRequest


class TournamentBase(SQLModel):
    name: str = Field(max_length=50)
    auto_accept_join_requests: bool = Field(default=True)


class Tournament(TournamentBase, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    event_id: uuid.UUID = Field(foreign_key="event.id", ondelete="CASCADE")

    player_links: list[TournamentPlayerLink] = Relationship(
        back_populates="tournament", cascade_delete=True
    )
    event: Event = Relationship(back_populates="tournaments")
    rounds: list["Round"] = Relationship(
        back_populates="tournament", cascade_delete=True
    )

    invitations: list["TournamentInvitation"] = Relationship(
        back_populates="tournament", cascade_delete=True
    )
    join_requests: list["TournamentJoinRequest"] = Relationship(
        back_populates="tournament", cascade_delete=True
    )

    def can_be_edited_by(self, user: User) -> bool:
        return self.event.can_be_edited_by(user)

    def can_be_deleted(self, user: User) -> bool:
        return user.is_super_admin or (
            self.event.can_be_deleted(user)
            and all(round.can_be_deleted(user) for round in self.rounds)
        )

    def has_started(self) -> bool:
        return any(round.has_started() for round in self.rounds)

    def get_players_by_nickname(self) -> list[Player]:
        players = [link.player for link in self.player_links]
        return sorted(players, key=lambda p: p.nickname)

    def get_rounds_by_order(self) -> list["Round"]:
        return sorted(self.rounds, key=lambda r: r.order_index)

    def add_player(self, player: Player, has_paid_entry: bool = False) -> None:
        if all(link.player_id != player.id for link in self.player_links):
            player_link = TournamentPlayerLink(
                player=player, tournament=self, has_paid_entry=has_paid_entry
            )
            self.player_links.append(player_link)

    def remove_player(self, player: Player) -> None:
        player_link = next(
            (link for link in self.player_links if link.player_id == player.id),
            None,
        )
        if player_link is not None:
            self.player_links.remove(player_link)


class TournamentCreate(TournamentBase):
    event_id: uuid.UUID


class TournamentPublic(TournamentBase):
    id: uuid.UUID
    event_id: uuid.UUID


class TournamentUpdate(SQLModel):
    name: str | None = None
