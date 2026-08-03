"""Database engine and session management for the BAMBO backend."""

import os
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.pool import StaticPool

from app.config import get_app_env, get_database_url, get_int_setting, is_sqlite_url

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
        else:
            engine_kwargs.update(
                pool_size=get_int_setting("DB_POOL_SIZE", 10),
                max_overflow=get_int_setting("DB_MAX_OVERFLOW", 10),
                pool_timeout=get_int_setting("DB_POOL_TIMEOUT_SECONDS", 30),
                pool_recycle=get_int_setting("DB_POOL_RECYCLE_SECONDS", 1800),
                connect_args={
                    "application_name": "bambo-backend",
                    "options": (
                        f"-c statement_timeout={get_int_setting('DB_STATEMENT_TIMEOUT_MS', 15000)} "
                        "-c timezone=UTC"
                    ),
                },
            )
            sslmode = os.getenv("DB_SSLMODE")
            if sslmode:
                engine_kwargs["connect_args"]["sslmode"] = sslmode

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
    if get_app_env() == "production" and is_sqlite_url():
        raise RuntimeError("SQLite is forbidden in production")
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
