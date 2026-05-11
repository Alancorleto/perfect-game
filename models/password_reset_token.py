import datetime
import secrets
import uuid

from sqlmodel import Field, Relationship, SQLModel

from models.user import User


class PasswordResetToken(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    user_id: uuid.UUID = Field(foreign_key="user.id")
    code: str = Field()
    issued_at: datetime.datetime = Field()
    expires_at: datetime.datetime = Field()
    used_at: datetime.datetime | None = Field(default=None)

    user: User = Relationship()

    @classmethod
    def create(
        cls, user_id: uuid.UUID, ttl: datetime.timedelta
    ) -> "PasswordResetToken":
        now = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)
        return cls(
            user_id=user_id,
            code=f"{secrets.randbelow(1_000_000):06d}",
            issued_at=now,
            expires_at=now + ttl,
            used_at=None,
        )
