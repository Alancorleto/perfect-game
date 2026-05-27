import uuid
from typing import TYPE_CHECKING

from sqlmodel import Field, Relationship, SQLModel

from models.category_player import CategoryPlayerLink
from models.player import Player
from models.tournament import Tournament
from models.user import User

if TYPE_CHECKING:
    from models.category_invitation import CategoryInvitation, CategoryJoinRequest
    from models.round import Round


class CategoryBase(SQLModel):
    name: str = Field(max_length=50)
    auto_accept_join_requests: bool = Field(default=True)


class Category(CategoryBase, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    tournament_id: uuid.UUID = Field(foreign_key="tournament.id", ondelete="CASCADE")

    player_links: list[CategoryPlayerLink] = Relationship(
        back_populates="category", cascade_delete=True
    )
    tournament: Tournament = Relationship(back_populates="categories")
    rounds: list["Round"] = Relationship(back_populates="category", cascade_delete=True)

    invitations: list["CategoryInvitation"] = Relationship(
        back_populates="category", cascade_delete=True
    )
    join_requests: list["CategoryJoinRequest"] = Relationship(
        back_populates="category", cascade_delete=True
    )

    def can_be_edited_by(self, user: User) -> bool:
        return self.tournament.can_be_edited_by(user)

    def can_be_deleted(self, user: User) -> bool:
        return user.is_super_admin or all(
            round.can_be_deleted(user) for round in self.rounds
        )

    def get_players_by_nickname(self) -> list[Player]:
        players = [link.player for link in self.player_links]
        return sorted(players, key=lambda p: p.nickname)

    def get_rounds_by_order(self) -> list["Round"]:
        return sorted(self.rounds, key=lambda r: r.order_index)

    def add_player(self, player: Player, has_paid_entry: bool = False) -> None:
        if all(link.player_id != player.id for link in self.player_links):
            player_link = CategoryPlayerLink(
                player=player, category=self, has_paid_entry=has_paid_entry
            )
            self.player_links.append(player_link)

    def remove_player(self, player: Player) -> None:
        player_link = next(
            (link for link in self.player_links if link.player_id == player.id),
            None,
        )
        if player_link is not None:
            self.player_links.remove(player_link)


class CategoryCreate(CategoryBase):
    tournament_id: uuid.UUID
