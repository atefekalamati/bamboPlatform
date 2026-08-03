"""Environment-backed application configuration."""

import os
from pathlib import Path
from urllib.parse import urlparse

from dotenv import load_dotenv

if os.getenv("APP_ENV", "development").lower() != "production":
    load_dotenv()

DEFAULT_DATABASE_URL = "postgresql+psycopg://bambo:bambo@localhost:5432/bambo"
DEFAULT_AUTH_SECRET = "development-only-change-me"
SUPPORTED_PRODUCTION_SMS_PROVIDERS: frozenset[str] = frozenset()


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


def get_bool_setting(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def get_int_setting(name: str, default: int) -> int:
    return int(os.getenv(name, str(default)))


def get_bootstrap_super_admin_mobile() -> str | None:
    return os.getenv("BOOTSTRAP_SUPER_ADMIN_MOBILE")


def get_cors_origins() -> list[str]:
    configured = os.getenv(
        "CORS_ORIGINS",
        "http://127.0.0.1:8080,http://localhost:8080",
    )
    return [origin.strip() for origin in configured.split(",") if origin.strip()]


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


def get_trusted_hosts() -> list[str]:
    configured = os.getenv("TRUSTED_HOSTS", "127.0.0.1,localhost,testserver")
    return [host.strip() for host in configured.split(",") if host.strip()]


def get_docs_enabled() -> bool:
    return get_bool_setting("ENABLE_API_DOCS", get_app_env() != "production")


def get_release_version() -> str:
    return os.getenv("RELEASE_VERSION", "development")


def get_log_level() -> str:
    level = os.getenv("LOG_LEVEL", "INFO").upper()
    if level not in {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}:
        raise RuntimeError("LOG_LEVEL is invalid")
    return level


def validate_production_settings() -> None:
    """Fail fast before a Production process accepts traffic."""
    if get_app_env() != "production":
        return

    errors: list[str] = []
    database_url = os.getenv("DATABASE_URL", "").strip()
    secret = os.getenv("AUTH_SECRET", "")
    origins = get_cors_origins()
    storage_root = get_dwg_storage_root()

    if not database_url.startswith(("postgresql://", "postgresql+psycopg://")):
        errors.append("DATABASE_URL must be an explicit PostgreSQL URL")
    if not secret or secret == DEFAULT_AUTH_SECRET or len(secret) < 32:
        errors.append("AUTH_SECRET must be a non-default value of at least 32 characters")
    if not origins or "*" in origins:
        errors.append("CORS_ORIGINS must contain explicit origins")
    for origin in origins:
        parsed = urlparse(origin)
        if parsed.scheme != "https" or not parsed.netloc:
            errors.append("CORS_ORIGINS must contain valid HTTPS origins")
            break
        if (parsed.hostname or "").lower() in {"localhost", "127.0.0.1", "::1"}:
            errors.append("CORS_ORIGINS must not contain localhost")
            break
    if os.getenv("DWG_MAX_BYTES") is None:
        errors.append("DWG_MAX_BYTES must be explicitly configured")
    else:
        try:
            if int(os.environ["DWG_MAX_BYTES"]) <= 0:
                raise ValueError
        except ValueError:
            errors.append("DWG_MAX_BYTES must be a positive integer")
    if get_dwg_storage_backend() != "local":
        errors.append("configured DWG storage backend is unsupported")
    try:
        storage_root.mkdir(parents=True, exist_ok=True)
        probe = storage_root / ".readiness-config-probe"
        probe.write_bytes(b"ok")
        probe.unlink()
    except OSError:
        errors.append("DWG_STORAGE_ROOT must be writable")
    sms_provider = os.getenv("SMS_PROVIDER", "").strip().lower()
    if sms_provider not in SUPPORTED_PRODUCTION_SMS_PROVIDERS:
        errors.append("no approved production SMS provider adapter is implemented")
    if get_bool_setting("DEBUG"):
        errors.append("DEBUG must be disabled")
    if get_docs_enabled():
        errors.append("ENABLE_API_DOCS must be disabled unless explicitly security-approved")
    trusted_hosts = get_trusted_hosts()
    if not trusted_hosts or "*" in trusted_hosts or any(
        host.lower() in {"localhost", "127.0.0.1"} for host in trusted_hosts
    ):
        errors.append("TRUSTED_HOSTS must contain explicit production hosts")
    if os.getenv("BOOTSTRAP_SUPER_ADMIN_MOBILE") and not get_bool_setting(
        "ALLOW_SUPER_ADMIN_BOOTSTRAP"
    ):
        errors.append("BOOTSTRAP_SUPER_ADMIN_MOBILE requires ALLOW_SUPER_ADMIN_BOOTSTRAP=true")
    forwarded_allow_ips = os.getenv("FORWARDED_ALLOW_IPS", "").strip()
    if not forwarded_allow_ips or forwarded_allow_ips == "*":
        errors.append("FORWARDED_ALLOW_IPS must identify trusted reverse proxies")
    for name, default in (
        ("AUTH_SESSION_TTL_SECONDS", 28800),
        ("OTP_TTL_SECONDS", 300),
        ("OTP_MAX_ATTEMPTS", 5),
        ("OTP_MAX_REQUESTS_PER_WINDOW", 5),
        ("OTP_MAX_IP_REQUESTS_PER_WINDOW", 20),
        ("OTP_RATE_WINDOW_SECONDS", 900),
        ("OTP_RESEND_COOLDOWN_SECONDS", 60),
    ):
        try:
            if get_int_setting(name, default) <= 0:
                raise ValueError
        except ValueError:
            errors.append(f"{name} must be a positive integer")

    if errors:
        raise RuntimeError("Invalid production configuration: " + "; ".join(errors))
