import uuid

from sqlmodel import SQLModel


class CategoryPublic(SQLModel):
    id: uuid.UUID
    name: str
    auto_accept_join_requests: bool
    tournament_id: uuid.UUID


class CategoryUpdate(SQLModel):
    name: str | None = None
    auto_accept_join_requests: bool | None = None
