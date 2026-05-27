import uuid

from sqlmodel import SQLModel

from schemas.category import CategoryPublic
from schemas.player import PlayerPublic


class CategoryPlayerLinkPublic(SQLModel):
    category_id: uuid.UUID
    player_id: uuid.UUID
    has_paid_entry: bool = False
    category: CategoryPublic
    player: PlayerPublic
