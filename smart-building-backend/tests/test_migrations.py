"""Regression tests for the Alembic schema contract."""

from io import StringIO
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect, text

import app.models  # noqa: F401
from app.database import Base

BACKEND_ROOT = Path(__file__).resolve().parents[1]


def alembic_config() -> Config:
    return Config(str(BACKEND_ROOT / "alembic.ini"))


def test_initial_migration_upgrades_matches_metadata_and_downgrades(monkeypatch, tmp_path):
    database_path = tmp_path / "migration.db"
    database_url = f"sqlite:///{database_path}"
    monkeypatch.setenv("DATABASE_URL", database_url)

    config = alembic_config()
    command.upgrade(config, "head")

    engine = create_engine(database_url)
    inspector = inspect(engine)
    migrated_tables = set(inspector.get_table_names())
    model_tables = set(Base.metadata.tables)
    assert migrated_tables == model_tables | {"alembic_version"}

    for table_name, table in Base.metadata.tables.items():
        migrated_columns = {column["name"] for column in inspector.get_columns(table_name)}
        assert migrated_columns == {column.name for column in table.columns}

    with engine.connect() as connection:
        assert (
            connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
            == "0002_auth_rbac_audit"
        )
    engine.dispose()

    command.check(config)
    command.downgrade(config, "base")
    downgraded_tables = set(inspect(create_engine(database_url)).get_table_names())
    assert downgraded_tables.isdisjoint(model_tables)


def test_initial_migration_compiles_for_postgresql(monkeypatch):
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql+psycopg://bambo:bambo@localhost:5432/bambo",
    )
    output = StringIO()
    config = alembic_config()
    config.output_buffer = output

    command.upgrade(config, "head", sql=True)

    sql = output.getvalue()
    assert "CREATE TABLE pilots" in sql
    assert "CREATE TABLE pilot_stages" in sql
    assert "JSONB" in sql
