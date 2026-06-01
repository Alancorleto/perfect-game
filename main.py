import os
from datetime import datetime, timedelta, timezone

from dotenv import load_dotenv

# Load environment variables from .env file in development
if os.getenv("ENVIRONMENT") != "production":
    load_dotenv()

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.exceptions import HTTPException
from fastapi.staticfiles import StaticFiles
from sqlmodel import SQLModel

from database import SessionDep, engine
from routers import api_router, tag_metadata


@asynccontextmanager
async def lifespan(app: FastAPI):
    create_db_and_tables()
    yield


app = FastAPI(lifespan=lifespan, openapi_tags=tag_metadata)
app.include_router(api_router)

if os.getenv("ENVIRONMENT") != "production":
    os.makedirs("image_storage_local", exist_ok=True)
    app.mount("/images", StaticFiles(directory="image_storage_local"), name="images")


def create_db_and_tables():
    SQLModel.metadata.create_all(engine, checkfirst=True)


@app.get("/health")
def health():
    return {"status": "ok"}
