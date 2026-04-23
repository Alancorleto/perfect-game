import os
from typing import Annotated
from fastapi import Depends
from sqlmodel import Session, create_engine

DATABASE_URL = os.getenv("DATABASE_URL")

connect_args = {}
if DATABASE_URL and DATABASE_URL.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

engine = create_engine(
    DATABASE_URL,
    echo=True,
    connect_args=connect_args,
)


def get_session():
    with Session(engine) as session:
        yield session


SessionDep = Annotated[Session, Depends(get_session)]
