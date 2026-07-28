"""Environment-backed application configuration."""

import os

from dotenv import load_dotenv

load_dotenv()

DEFAULT_DATABASE_URL = "postgresql+psycopg://bambo:bambo@localhost:5432/bambo"


def get_database_url() -> str:
    """Return the current database URL, allowing tests to replace it at runtime."""
    return os.getenv("DATABASE_URL", DEFAULT_DATABASE_URL)


def is_sqlite_url(database_url: str | None = None) -> bool:
    return (database_url or get_database_url()).startswith("sqlite")
