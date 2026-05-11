import os
import uuid
from datetime import datetime, timedelta, timezone
from typing import Annotated

import jwt
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi_mail import ConnectionConfig, FastMail, MessageSchema, MessageType
from jwt.exceptions import InvalidTokenError
from pwdlib import PasswordHash
from sqlmodel import Session, select

from database import SessionDep
from models.password_reset_token import PasswordResetToken
from models.refresh_token import RefreshToken
from models.user import (
    PasswordResetConfirm,
    PasswordResetRequest,
    Token,
    TokenData,
    User,
    UserCreate,
    UserPublic,
    UserUpdate,
)

PASSWORD_RESET_TOKEN_EXPIRE_MINUTES = 60

mail_config = ConnectionConfig(
    MAIL_USERNAME=os.getenv("MAIL_USERNAME", ""),
    MAIL_PASSWORD=os.getenv("MAIL_PASSWORD", ""),
    MAIL_FROM=os.getenv("MAIL_FROM", "noreply@example.com"),
    MAIL_PORT=int(os.getenv("MAIL_PORT", "587")),
    MAIL_SERVER=os.getenv("MAIL_SERVER", "smtp.example.com"),
    MAIL_STARTTLS=os.getenv("MAIL_STARTTLS", "true").lower() == "true",
    MAIL_SSL_TLS=os.getenv("MAIL_SSL_TLS", "false").lower() == "true",
    USE_CREDENTIALS=True,
    VALIDATE_CERTS=True,
)

fast_mail = FastMail(mail_config)

SECRET_KEY = os.getenv("JWT_SECRET_KEY")
ALGORITHM = os.getenv("JWT_ALGORITHM")
ACCESS_TOKEN_EXPIRE_MINUTES = 30

router = APIRouter(tags=["users"])

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

password_hash = PasswordHash.recommended()

DUMMY_HASH = password_hash.hash("dummypassword")


def verify_password(plain_password, hashed_password):
    return password_hash.verify(plain_password, hashed_password)


def get_password_hash(password):
    return password_hash.hash(password)


def get_user_by_email(email: str, session: Session):
    user = session.exec(select(User).where(User.email == email)).first()
    if not user:
        return None
    return user


def authenticate_user(email: str, password: str, session: Session):
    user = get_user_by_email(email, session)
    if not user:
        verify_password(password, DUMMY_HASH)
        return False
    if not verify_password(password, user.hashed_password):
        return False
    return user


def create_access_token(data: dict, expires_delta: timedelta | None = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)], session: SessionDep
):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_data = TokenData(username=username)
    except InvalidTokenError:
        raise credentials_exception

    user = get_user_by_email(email=token_data.username, session=session)
    if user is None:
        raise credentials_exception

    return user


UserDep = Annotated[User, Depends(get_current_user)]


@router.post("/users", response_model=UserPublic)
async def create_user(user: UserCreate, session: SessionDep):
    existing_email = session.exec(select(User).where(User.email == user.email)).first()
    if existing_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    password = get_password_hash(user.password)

    db_user = User(
        email=user.email,
        hashed_password=password,
    )

    session.add(db_user)
    session.commit()
    session.refresh(db_user)

    return db_user


@router.post("/token", response_model=Token)
async def login(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    session: SessionDep,
) -> Token:
    user = authenticate_user(form_data.username, form_data.password, session)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )

    refresh_token = RefreshToken.create(user_id=user.id, ttl=timedelta(days=30))
    session.add(refresh_token)
    session.commit()

    return Token(
        access_token=access_token,
        token_type="bearer",
        refresh_token=refresh_token.token,
    )


@router.post("/token/refresh", response_model=Token)
async def refresh_access_token(refresh_token: str, session: SessionDep) -> Token:
    now = datetime.now(timezone.utc).replace(tzinfo=None)

    db_token = session.get(RefreshToken, refresh_token)

    if not db_token or db_token.revoked_at is not None or db_token.expires_at < now:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        )

    new_access_token = create_access_token(
        data={"sub": db_token.user.email},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
    )

    return Token(
        access_token=new_access_token,
        token_type="bearer",
        refresh_token=refresh_token,
    )


@router.post("/token/revoke")
async def revoke_refresh_token(refresh_token: str, session: SessionDep) -> dict:
    db_token = session.get(RefreshToken, refresh_token)
    if db_token:
        db_token.revoked_at = datetime.now(timezone.utc).replace(tzinfo=None)
        session.commit()
    return {"detail": "Token revoked"}


@router.get("/users/me", response_model=UserPublic)
async def get_currently_logged_user(
    current_user: UserDep,
):
    return current_user


@router.get("/users", response_model=list[UserPublic])
async def list_users(session: SessionDep):
    users = session.exec(select(User)).all()
    return users


@router.get("/users/{user_id}", response_model=UserPublic)
async def get_user(user_id: uuid.UUID, session: SessionDep):
    user = session.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.put("/users/{user_id}", response_model=UserPublic)
async def update_user(
    user_id: uuid.UUID,
    session: SessionDep,
    logged_user: UserDep,
    user_update: UserUpdate,
):
    db_user = session.get(User, user_id)
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    if db_user.id != logged_user.id and not logged_user.is_super_admin:
        raise HTTPException(status_code=403, detail="Not authorized")

    user_data = user_update.model_dump(exclude_unset=True)
    db_user.sqlmodel_update(user_data)

    if user_update.password:
        hashed_password = get_password_hash(user_update.password)
        db_user.hashed_password = hashed_password

    session.add(db_user)
    session.commit()
    session.refresh(db_user)

    return db_user


@router.delete("/users/{user_id}")
async def delete_user(user_id: uuid.UUID, session: SessionDep, logged_user: UserDep):
    db_user = session.get(User, user_id)
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    if db_user.id != logged_user.id and not logged_user.is_super_admin:
        raise HTTPException(status_code=403, detail="Not authorized")

    session.delete(db_user)
    session.commit()

    return {"detail": "User deleted"}


@router.post("/password-reset/request")
async def request_password_reset(
    body: PasswordResetRequest, session: SessionDep
) -> dict:
    """Requests a password reset for the given email address.

    Always returns the same message to prevent email enumeration.
    """
    user = get_user_by_email(body.email, session)

    if user:
        reset_token = PasswordResetToken.create(
            user_id=user.id,
            ttl=timedelta(minutes=PASSWORD_RESET_TOKEN_EXPIRE_MINUTES),
        )
        session.add(reset_token)
        session.commit()

        message = MessageSchema(
            subject="Password reset request",
            recipients=[body.email],
            body=(
                f"Hi,\n\n"
                f"We received a request to reset the password for your account.\n\n"
                f"Your password reset code is:\n\n"
                f"{reset_token.code}\n\n"
                f"This code is valid for {PASSWORD_RESET_TOKEN_EXPIRE_MINUTES} minutes.\n\n"
                f"If you did not request this, you can safely ignore this email.\n"
            ),
            subtype=MessageType.plain,
        )
        await fast_mail.send_message(message)

    return {
        "detail": "If the email exists, you will receive a link to reset your password."
    }


@router.post("/password-reset/confirm")
async def confirm_password_reset(
    body: PasswordResetConfirm, session: SessionDep
) -> dict:
    """Resets the password using the 6-digit code received by email."""
    now = datetime.now(timezone.utc).replace(tzinfo=None)

    user = get_user_by_email(body.email, session)
    db_token = (
        session.exec(
            select(PasswordResetToken)
            .where(PasswordResetToken.user_id == user.id)
            .where(PasswordResetToken.code == body.code)
            .where(PasswordResetToken.used_at == None)  # noqa: E711
            .where(PasswordResetToken.expires_at > now)
        ).first()
        if user
        else None
    )

    if not db_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired token.",
        )

    db_token.user.hashed_password = get_password_hash(body.new_password)
    db_token.used_at = now

    session.add(db_token)
    session.commit()

    return {"detail": "Password updated successfully."}
