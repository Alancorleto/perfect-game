import uuid
from enum import Enum

from sqlmodel import Field, Relationship, SQLModel

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

    category: Category = Relationship(back_populates="invitations")
    player: Player = Relationship(back_populates="category_invitations")


class CategoryInvitationPublic(SQLModel):
    category_id: uuid.UUID
    player: Player
    status: RequestStatus = Field(default=RequestStatus.PENDING)


class CategoryJoinRequest(CategoryRequestBase, table=True):
    category_id: uuid.UUID = Field(
        primary_key=True, foreign_key="category.id", ondelete="CASCADE"
    )
    player_id: uuid.UUID = Field(
        primary_key=True, foreign_key="player.id", ondelete="CASCADE"
    )

    category: Category = Relationship(back_populates="join_requests")
    player: Player = Relationship(back_populates="category_join_requests")


class CategoryJoinRequestPublic(CategoryRequestBase):
    player_id: uuid.UUID
    category: Category
    status: RequestStatus = Field(default=RequestStatus.PENDING)
