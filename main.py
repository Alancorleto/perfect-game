import os
from dotenv import load_dotenv

# Load environment variables from .env file in development
if os.getenv("ENVIRONMENT") != "production":
    load_dotenv()

from contextlib import asynccontextmanager
from fastapi import FastAPI
from sqlmodel import SQLModel
from routers import api_router
from database import engine


@asynccontextmanager
async def lifespan(app: FastAPI):
    create_db_and_tables()
    yield


app = FastAPI(lifespan=lifespan)
app.include_router(api_router)


def create_db_and_tables():
    SQLModel.metadata.create_all(engine, checkfirst=True)


@app.get("/health")
def health():
    return {"status": "ok"}
