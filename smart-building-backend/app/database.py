"""Database engine and session management for the BAMBO backend."""

from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.pool import StaticPool

from app.config import get_database_url, is_sqlite_url

engine = None
SessionLocal = sessionmaker(autocommit=False, autoflush=False, future=True, bind=None)

Base = declarative_base()


def get_engine():
    """Create or refresh the SQLAlchemy engine for the current DATABASE_URL."""
    global engine

    database_url = get_database_url()
    if engine is None or str(engine.url) != database_url:
        if engine is not None:
            engine.dispose()
        engine_kwargs = {"future": True, "pool_pre_ping": True}
        if is_sqlite_url(database_url):
            engine_kwargs["connect_args"] = {"check_same_thread": False}
            if database_url == "sqlite:///:memory:":
                engine_kwargs["poolclass"] = StaticPool

        engine = create_engine(database_url, **engine_kwargs)
        SessionLocal.configure(bind=engine)
    return engine


def get_session():
    """Create a database session bound to the current engine."""
    get_engine()
    return SessionLocal()


def init_db() -> None:
    """Create tables for isolated SQLite tests; production uses Alembic."""
    import app.models  # noqa: F401

    with get_engine().begin() as connection:
        Base.metadata.create_all(bind=connection)


def ensure_schema() -> None:
    """Keep SQLite test/dev startup convenient without bypassing production migrations."""
    if is_sqlite_url():
        init_db()


def get_db() -> Generator:
    """Provide a database session for FastAPI dependency injection."""
    get_engine()
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
