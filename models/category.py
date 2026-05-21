import uuid
from typing import TYPE_CHECKING

from sqlmodel import Field, Relationship, SQLModel

from models.category_invitation import CategoryInvitation, CategoryJoinRequest
from models.category_player import CategoryPlayerLink
from models.player import Player
from models.tournament import Tournament
from models.user import User

if TYPE_CHECKING:
    from models.round import Round


class CategoryBase(SQLModel):
    name: str
    auto_accept_join_requests: bool = Field(default=False)


class Category(CategoryBase, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    tournament_id: uuid.UUID = Field(foreign_key="tournament.id", ondelete="CASCADE")

    players: list[Player] = Relationship(link_model=CategoryPlayerLink)
    tournament: Tournament = Relationship(back_populates="categories")
    rounds: list["Round"] = Relationship(back_populates="category", cascade_delete=True)

    invitations: list[CategoryInvitation] = Relationship(
        back_populates="category", cascade_delete=True
    )
    join_requests: list[CategoryJoinRequest] = Relationship(
        back_populates="category", cascade_delete=True
    )

    def can_be_edited_by(self, user: User) -> bool:
        return self.tournament.can_be_edited_by(user)

    def can_be_deleted(self, user: User) -> bool:
        return user.is_super_admin or all(
            round.can_be_deleted(user) for round in self.rounds
        )


class CategoryCreate(CategoryBase):
    tournament_id: uuid.UUID


class CategoryPublic(CategoryBase):
    id: uuid.UUID
    tournament_id: uuid.UUID


class CategoryUpdate(SQLModel):
    name: str | None = None
