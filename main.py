from fastapi import FastAPI
from sqlmodel import Field, Session, SQLModel, create_engine, select
import os
from routers import api_router

app = FastAPI()
app.include_router(api_router)

# The database URL is automatically injected as an environment variable
engine = create_engine(os.getenv("DATABASE_URL", "sqlite:///local_test_database.db"))


@app.get("/")
def main():
    return {"message": "Hello World"}


def create_db_and_tables():
    SQLModel.metadata.create_all(engine)


@app.on_event("startup")
def on_startup():
    create_db_and_tables()
