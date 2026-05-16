import datetime
import secrets
import uuid

from sqlmodel import Field, Relationship, SQLModel

from models.user import User


class RefreshToken(SQLModel, table=True):
    token: str = Field(primary_key=True)
    user_id: uuid.UUID = Field(foreign_key="user.id", ondelete="CASCADE")
    issued_at: datetime.datetime = Field()
    expires_at: datetime.datetime = Field()
    revoked_at: datetime.datetime | None = Field()

    user: User = Relationship()

    @classmethod
    def create(cls, user_id: uuid.UUID, ttl: datetime.timedelta) -> "RefreshToken":
        now = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)
        return cls(
            token=secrets.token_hex(32),
            user_id=user_id,
            issued_at=now,
            expires_at=now + ttl,
            revoked_at=None,
        )
