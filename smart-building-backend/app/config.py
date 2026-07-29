"""Environment-backed application configuration."""

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

DEFAULT_DATABASE_URL = "postgresql+psycopg://bambo:bambo@localhost:5432/bambo"
DEFAULT_AUTH_SECRET = "development-only-change-me"


def get_database_url() -> str:
    """Return the current database URL, allowing tests to replace it at runtime."""
    return os.getenv("DATABASE_URL", DEFAULT_DATABASE_URL)


def is_sqlite_url(database_url: str | None = None) -> bool:
    return (database_url or get_database_url()).startswith("sqlite")


def get_app_env() -> str:
    return os.getenv("APP_ENV", "development").lower()


def get_auth_secret() -> str:
    secret = os.getenv("AUTH_SECRET", DEFAULT_AUTH_SECRET)
    if get_app_env() == "production" and secret == DEFAULT_AUTH_SECRET:
        raise RuntimeError("AUTH_SECRET must be configured in production")
    return secret


def get_int_setting(name: str, default: int) -> int:
    return int(os.getenv(name, str(default)))


def get_bootstrap_super_admin_mobile() -> str | None:
    return os.getenv("BOOTSTRAP_SUPER_ADMIN_MOBILE")


def get_dwg_storage_root() -> Path:
    return Path(os.getenv("DWG_STORAGE_ROOT", "./storage/dwg")).resolve()


def get_dwg_max_bytes() -> int:
    configured = os.getenv("DWG_MAX_BYTES")
    if get_app_env() == "production" and configured is None:
        raise RuntimeError("DWG_MAX_BYTES must be configured in production")
    return int(configured or str(50 * 1024 * 1024))


def get_dwg_storage_backend() -> str:
    backend = os.getenv("DWG_STORAGE_BACKEND", "local")
    if backend != "local":
        raise RuntimeError(f"Unsupported DWG storage backend: {backend}")
    return backend
