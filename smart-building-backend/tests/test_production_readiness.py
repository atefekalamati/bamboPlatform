import pytest

from app.config import validate_production_settings


def test_production_configuration_fails_closed(monkeypatch, tmp_path):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("DATABASE_URL", "sqlite:///unsafe.db")
    monkeypatch.setenv("AUTH_SECRET", "short")
    monkeypatch.setenv("CORS_ORIGINS", "*")
    monkeypatch.setenv("TRUSTED_HOSTS", "*")
    monkeypatch.setenv("DWG_STORAGE_ROOT", str(tmp_path))
    monkeypatch.delenv("DWG_MAX_BYTES", raising=False)
    monkeypatch.setenv("SMS_PROVIDER", "fake")
    monkeypatch.setenv("DEBUG", "true")
    monkeypatch.setenv("ENABLE_API_DOCS", "true")

    with pytest.raises(RuntimeError) as exc_info:
        validate_production_settings()

    message = str(exc_info.value)
    assert "DATABASE_URL" in message
    assert "AUTH_SECRET" in message
    assert "CORS_ORIGINS" in message
    assert "DWG_MAX_BYTES" in message
    assert "SMS provider" in message
    assert "TRUSTED_HOSTS" in message


def test_production_cannot_claim_readiness_without_implemented_sms_adapter(
    monkeypatch,
    tmp_path,
):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql+psycopg://runtime@db:5432/bambo?sslmode=require",
    )
    monkeypatch.setenv("AUTH_SECRET", "a-secure-runtime-secret-with-more-than-32-characters")
    monkeypatch.setenv("CORS_ORIGINS", "https://pilot.example.invalid")
    monkeypatch.setenv("TRUSTED_HOSTS", "api.example.invalid")
    monkeypatch.setenv("DWG_STORAGE_ROOT", str(tmp_path))
    monkeypatch.setenv("DWG_MAX_BYTES", "52428800")
    monkeypatch.setenv("SMS_PROVIDER", "provider-without-an-adapter")
    monkeypatch.setenv("ENABLE_API_DOCS", "false")
    monkeypatch.setenv("DEBUG", "false")
    monkeypatch.setenv("FORWARDED_ALLOW_IPS", "10.0.0.10")

    with pytest.raises(RuntimeError, match="no approved production SMS provider adapter"):
        validate_production_settings()


def test_health_endpoints_and_security_headers(client):
    live = client.get("/health/live", headers={"X-Request-ID": "readiness-test"})
    assert live.status_code == 200
    assert live.json() == {"status": "live"}
    assert live.headers["x-request-id"] == "readiness-test"
    assert live.headers["x-content-type-options"] == "nosniff"

    ready = client.get("/health/ready")
    assert ready.status_code == 200
    assert ready.json()["status"] == "ready"
    assert all(ready.json()["checks"].values())

    version = client.get("/version")
    assert version.status_code == 200
    assert version.json()["service"] == "bambo-backend"


def test_sensitive_routes_are_not_cacheable(client, super_admin_headers):
    response = client.get("/auth/me", headers=super_admin_headers)
    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"
