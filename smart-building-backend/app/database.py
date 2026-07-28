"""Database configuration and session management for the smart building backend."""

import os
from datetime import datetime
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool
from sqlalchemy.orm import declarative_base, sessionmaker

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./smart_building.db")

engine = None
SessionLocal = sessionmaker(autocommit=False, autoflush=False, future=True, bind=None)

Base = declarative_base()


def get_engine():
    """Create or refresh the SQLAlchemy engine for the current DATABASE_URL."""
    global engine

    if engine is None or str(engine.url) != DATABASE_URL:
        engine_kwargs = {"future": True}
        if DATABASE_URL.startswith("sqlite"):
            engine_kwargs["connect_args"] = {"check_same_thread": False}
            if DATABASE_URL == "sqlite:///:memory:":
                engine_kwargs["poolclass"] = StaticPool

        engine = create_engine(DATABASE_URL, **engine_kwargs)
        SessionLocal.configure(bind=engine)
    return engine


def get_session():
    """Create a database session bound to the current engine."""
    engine = get_engine()
    return sessionmaker(autocommit=False, autoflush=False, future=True, bind=engine)()

    return engine


def init_db() -> None:
    """Create all database tables."""
    from app.models.building import Building  # noqa: F401
    from app.models.equipment import Equipment  # noqa: F401
    from app.models.sensor import Sensor  # noqa: F401

    with get_engine().begin() as connection:
        Base.metadata.create_all(bind=connection)
    return None


def ensure_schema() -> None:
    """Ensure the database schema exists before using sessions."""
    init_db()


def get_db() -> Generator:
    """Provide a database session for FastAPI dependency injection."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
