import os
from datetime import datetime, timedelta, timezone

from dotenv import load_dotenv

# Load environment variables from .env file in development
if os.getenv("ENVIRONMENT") != "production":
    load_dotenv()

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.exceptions import HTTPException
from sqlmodel import SQLModel

from database import SessionDep, engine
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


@app.delete("/")
async def clear_test_database(session: SessionDep):
    if os.getenv("ENVIRONMENT") != "production":
        session.expunge_all()
        session.commit()
    else:
        raise HTTPException(status_code=403, detail="not allowed in production")
    return {"detail": "all objects deleted"}
