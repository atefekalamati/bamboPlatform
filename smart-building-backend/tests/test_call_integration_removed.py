"""Guards that the call subsystem stays removed from the backend.

Migration 0021 dropped the call tables and 0d2997e deleted the routers, models,
schemas, services and RBAC entries. These assertions fail loudly if any of it
comes back by accident — a reintroduction has to be a deliberate change to this
file, not a silent merge.
"""

import pkgutil

import pytest

import app.models
from app.database import Base
from app.main import app
from app.rbac import ALL_PERMISSION_CODES, PERMISSIONS, SYSTEM_ROLES
from app.workflow import STAGE_DEFINITIONS

REMOVED_PERMISSIONS = (
    "calls.read",
    "calls.initiate",
    "calls.retry",
    "calls.override",
    "calls.record_outcome",
    "calls.recording.read",
)

REMOVED_ROUTES = (
    "/api/v1/pilots/{pilot_id}/stages/{stage_number}/calls",
    "/api/v1/calls/{call_id}/outcome",
    "/api/v1/calls/{call_id}/override",
    "/api/v1/calls/{call_id}/retry",
    "/api/v1/calls/{call_id}/recording-reference",
)

# Stages whose UI used to host a call panel.
CALL_ERA_STAGES = (5, 11, 13, 16, 18)


def test_openapi_exposes_no_call_endpoint():
    paths = app.openapi()["paths"]
    assert [path for path in paths if "call" in path.lower()] == []
    for route in REMOVED_ROUTES:
        assert route not in paths


def test_rbac_has_no_call_permission():
    assert [code for code in ALL_PERMISSION_CODES if code.startswith("calls.")] == []
    for code in REMOVED_PERMISSIONS:
        assert code not in ALL_PERMISSION_CODES
    assert [entry for entry in PERMISSIONS if entry[1] == "calls"] == []


def test_no_system_role_grants_a_call_permission():
    for role, (_display, codes) in SYSTEM_ROLES.items():
        offenders = [code for code in codes if code.startswith("calls.")]
        assert offenders == [], f"{role} still grants {offenders}"


def test_orm_metadata_has_no_call_table():
    assert [name for name in Base.metadata.tables if "call" in name] == []


def test_no_call_module_is_importable():
    packages = ["app.models", "app.routers", "app.services", "app.schemas", "app.providers"]
    for package_name in packages:
        package = __import__(package_name, fromlist=["__path__"])
        modules = [name for _, name, _ in pkgutil.iter_modules(package.__path__)]
        assert "calls" not in modules, f"{package_name}.calls is back"


@pytest.mark.parametrize("stage_number", CALL_ERA_STAGES)
def test_call_era_stages_require_nothing_call_related(stage_number):
    stage = next(item for item in STAGE_DEFINITIONS if item.number == stage_number)
    requirements = " ".join(stage.required_checklist + stage.required_form_fields).lower()
    for term in ("call", "recording", "outcome_reference", "astel"):
        assert term not in requirements, f"stage {stage_number} still requires {term!r}"


def test_stage_18_requirements_are_follow_up_only():
    """Stage 18 is the one the UI marked as call-gated."""
    stage = next(item for item in STAGE_DEFINITIONS if item.number == 18)
    assert stage.required_checklist == ("follow_up_registered",)
    assert stage.required_form_fields == (
        "obstacle",
        "action",
        "owner",
        "due_at",
        "result",
    )


def test_call_routes_return_404(client, super_admin_headers):
    """Live check through the app, not just the schema."""
    for method, path in (
        ("GET", "/api/v1/pilots/1/stages/18/calls"),
        ("POST", "/api/v1/pilots/1/stages/18/calls"),
        ("PATCH", "/api/v1/calls/1/outcome"),
        ("POST", "/api/v1/calls/1/override"),
        ("POST", "/api/v1/calls/1/retry"),
        ("GET", "/api/v1/calls/1/recording-reference"),
    ):
        response = client.request(method, path, json={}, headers=super_admin_headers)
        assert response.status_code == 404, f"{method} {path} -> {response.status_code}"


def test_super_admin_permission_payload_carries_no_call_permission(
    client,
    super_admin_headers,
):
    payload = client.get("/auth/me", headers=super_admin_headers).json()
    assert [code for code in payload["permissions"] if code.startswith("calls.")] == []
