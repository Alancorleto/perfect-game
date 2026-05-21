import uuid
from enum import Enum
from typing import TYPE_CHECKING

from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from models.category import Category
    from models.player import Player


class RequestStatus(Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    DECLINED = "declined"


class CategoryRequestBase(SQLModel):
    status: RequestStatus = Field(default=RequestStatus.PENDING)


class CategoryInvitation(CategoryRequestBase, table=True):
    category_id: uuid.UUID = Field(
        primary_key=True, foreign_key="category.id", ondelete="CASCADE"
    )
    player_id: uuid.UUID = Field(
        primary_key=True, foreign_key="player.id", ondelete="CASCADE"
    )

    category: "Category" = Relationship(back_populates="invitations")
    player: "Player" = Relationship()


class CategoryInvitationPublic(CategoryRequestBase):
    category: "Category"
    player: "Player"


class CategoryJoinRequest(CategoryRequestBase, table=True):
    category_id: uuid.UUID = Field(
        primary_key=True, foreign_key="category.id", ondelete="CASCADE"
    )
    player_id: uuid.UUID = Field(
        primary_key=True, foreign_key="player.id", ondelete="CASCADE"
    )

    category: "Category" = Relationship(back_populates="join_requests")
    player: "Player" = Relationship()


class CategoryJoinRequestPublic(CategoryRequestBase):
    category: "Category"
    player: "Player"
