import os
from datetime import datetime, timedelta, timezone

from dotenv import load_dotenv

# Load environment variables from .env file in development
if os.getenv("ENVIRONMENT") != "production":
    load_dotenv()

from contextlib import asynccontextmanager
from typing import Annotated

import jwt
from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.staticfiles import StaticFiles
from jwt.exceptions import InvalidTokenError
from pwdlib import PasswordHash
from pydantic import BaseModel
from sqlmodel import SQLModel

from database import engine
from routers import api_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    create_db_and_tables()
    yield


app = FastAPI(lifespan=lifespan)
app.include_router(api_router)
app.mount("/images", StaticFiles(directory="image_storage_local"), name="images")


def create_db_and_tables():
    SQLModel.metadata.create_all(engine, checkfirst=True)


@app.get("/health")
def health():
    return {"status": "ok"}
