import uuid
from sqlmodel import Field, SQLModel


class CategoryPlayerLink(SQLModel, table=True):
    category_id: uuid.UUID = Field(foreign_key="category.id", primary_key=True)
    player_id: uuid.UUID = Field(foreign_key="player.id", primary_key=True)