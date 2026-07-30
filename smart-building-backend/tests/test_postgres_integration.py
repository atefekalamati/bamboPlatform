"""Live PostgreSQL schema and persistence checks used by Backend CI."""

import os

import pytest
from sqlalchemy import inspect, text
from sqlalchemy.dialects.postgresql import JSONB

import app.database as database
import app.models  # noqa: F401
from app.models import Pilot
from app.schemas.workflow import PilotCreate
from app.services.security import seed_security_data
from app.services.workflow import create_pilot

POSTGRES_TEST_DATABASE_URL = os.getenv("POSTGRES_TEST_DATABASE_URL")

pytestmark = pytest.mark.skipif(
    not POSTGRES_TEST_DATABASE_URL,
    reason="POSTGRES_TEST_DATABASE_URL is not configured",
)


def _column_type(inspector, table_name: str, column_name: str):
    return next(
        column["type"]
        for column in inspector.get_columns(table_name)
        if column["name"] == column_name
    )


def test_postgresql_schema_and_persistence(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", POSTGRES_TEST_DATABASE_URL)
    engine = database.get_engine()
    assert engine.dialect.name == "postgresql"

    inspector = inspect(engine)
    assert set(inspector.get_table_names()) == set(database.Base.metadata.tables) | {
        "alembic_version"
    }
    assert isinstance(
        _column_type(inspector, "stage_submissions", "form_data"),
        JSONB,
    )
    assert isinstance(
        _column_type(inspector, "audit_logs", "new_data"),
        JSONB,
    )
    assert isinstance(
        _column_type(inspector, "commercial_proposals", "features"),
        JSONB,
    )
    with engine.connect() as connection:
        assert (
            connection.execute(
                text("SELECT version_num FROM alembic_version")
            ).scalar_one()
            == "0008_incident_unique_cleanup"
        )

    with database.get_session() as db:
        seed_security_data(db)
        pilot = create_pilot(
            db,
            PilotCreate.model_validate(
                {
                    "pilot_year": 1499,
                    "owner": {
                        "name": "PostgreSQL CI Owner",
                        "decision_maker_name": "CI Decision Maker",
                        "decision_maker_position": "Director",
                        "primary_mobile": "09151112233",
                    },
                    "project": {
                        "name": "PostgreSQL integration project",
                        "total_floors": 2,
                        "address": "CI integration environment",
                        "progress_stage": "active",
                        "customer_need": "Verify PostgreSQL persistence",
                        "expected_value": "Prevent production schema regressions",
                    },
                }
            ),
        )
        pilot_id = pilot.id

    with database.get_session() as db:
        persisted = db.get(Pilot, pilot_id)
        assert persisted is not None
        assert persisted.code == "PIL-1499-001"
        assert persisted.project.system_name == persisted.project_system_name
        assert len(persisted.stages) == 19
        assert len(persisted.gates) == 5

    engine.dispose()
