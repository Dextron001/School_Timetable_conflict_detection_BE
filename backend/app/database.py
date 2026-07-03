"""Database engine, session factory and Base.

We use SQLite for zero-config local development (great for a project defence).
Swapping to Postgres later is just a DATABASE_URL change.
"""
import os

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

load_dotenv()  # reads backend/.env

DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///./timetable.db")

# SQLAlchemy needs a different driver prefix for Postgres
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

connect_args = {}
if DATABASE_URL.startswith("sqlite"):
    connect_args["check_same_thread"] = False  # needed for SQLite + FastAPI threads

engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    """FastAPI dependency that yields a DB session and always closes it."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()