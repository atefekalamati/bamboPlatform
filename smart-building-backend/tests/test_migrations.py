"""Regression tests for the Alembic schema contract."""

from io import StringIO
from pathlib import Path

from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine, inspect, text

import app.models  # noqa: F401
from app.database import Base

BACKEND_ROOT = Path(__file__).resolve().parents[1]


def alembic_config() -> Config:
    return Config(str(BACKEND_ROOT / "alembic.ini"))


def expected_migration_head() -> str:
    """Read the head from the scripts so a new migration cannot go stale here."""
    heads = ScriptDirectory.from_config(alembic_config()).get_heads()
    assert len(heads) == 1, f"expected exactly one alembic head, found {heads}"
    return heads[0]


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

    proposal_columns = {
        column["name"]: column
        for column in inspector.get_columns("commercial_proposals")
    }
    assert proposal_columns["proposal_file_name"]["nullable"] is True
    assert proposal_columns["proposal_file_size"]["nullable"] is True
    assert proposal_columns["proposal_file_sha256"]["nullable"] is True
    proposal_checks = {
        constraint["name"]
        for constraint in inspector.get_check_constraints("commercial_proposals")
    }
    assert "ck_commercial_proposal_file_metadata" in proposal_checks

    with engine.connect() as connection:
        assert (
            connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
            == expected_migration_head()
        )
        existing_permission = connection.execute(
            text("SELECT can_edit_own_name FROM users LIMIT 1")
        ).first()
        if existing_permission is not None:
            assert existing_permission[0] in (False, 0)
    assert {
        column["name"] for column in inspector.get_columns("form_f04")
    } >= {"other_issue_description"}
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
    assert "ALTER TABLE alembic_version ALTER COLUMN version_num TYPE VARCHAR(128)" in sql
    assert "ALTER TABLE incidents DROP CONSTRAINT incidents_code_key" in sql
    assert "ck_commercial_proposal_file_metadata" in sql
    assert "other_issue_description" in sql
    assert "can_edit_own_name" in sql
    assert "refresh_token_hash" in sql
    assert "DROP TABLE calls" in sql


def test_remove_call_integration_migration_drops_tables_and_rolls_back(monkeypatch, tmp_path):
    database_path = tmp_path / "remove-call-integration.db"
    database_url = f"sqlite:///{database_path}"
    monkeypatch.setenv("DATABASE_URL", database_url)
    config = alembic_config()

    command.upgrade(config, "0020_refresh_tokens")
    inspector = inspect(create_engine(database_url))
    assert {"calls", "call_attempts", "call_outcomes", "call_webhook_events"}.issubset(
        set(inspector.get_table_names())
    )

    command.upgrade(config, "0021_remove_call_integration")
    tables = set(inspect(create_engine(database_url)).get_table_names())
    assert {"calls", "call_attempts", "call_outcomes", "call_webhook_events"}.isdisjoint(tables)

    command.downgrade(config, "0020_refresh_tokens")
    tables = set(inspect(create_engine(database_url)).get_table_names())
    assert {"calls", "call_attempts", "call_outcomes", "call_webhook_events"}.issubset(tables)


def test_refresh_token_migration_adds_session_fields_and_rolls_back(monkeypatch, tmp_path):
    database_path = tmp_path / "refresh-token-migration.db"
    database_url = f"sqlite:///{database_path}"
    monkeypatch.setenv("DATABASE_URL", database_url)
    config = alembic_config()

    command.upgrade(config, "0019_user_own_name_edit_permission")
    command.upgrade(config, "0020_refresh_tokens")
    columns = {
        column["name"]
        for column in inspect(create_engine(database_url)).get_columns("auth_sessions")
    }
    assert {
        "refresh_token_hash",
        "previous_refresh_token_hash",
        "refresh_expires_at",
        "refresh_used_at",
        "ip_address",
        "user_agent",
    }.issubset(columns)

    command.downgrade(config, "0019_user_own_name_edit_permission")
    columns = {
        column["name"]
        for column in inspect(create_engine(database_url)).get_columns("auth_sessions")
    }
    assert "refresh_token_hash" not in columns


def test_own_name_edit_permission_migrates_existing_users_and_rolls_back(monkeypatch, tmp_path):
    database_path = tmp_path / "own-name-permission.db"
    database_url = f"sqlite:///{database_path}"
    monkeypatch.setenv("DATABASE_URL", database_url)
    config = alembic_config()

    command.upgrade(config, "0018_call_integration")
    engine = create_engine(database_url)
    with engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO users "
                "(mobile, display_name, is_active, created_at, updated_at) "
                "VALUES ('+989151111111', 'کاربر قبلی', 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"
            )
        )
    engine.dispose()

    command.upgrade(config, "0019_user_own_name_edit_permission")
    engine = create_engine(database_url)
    with engine.connect() as connection:
        assert connection.execute(
            text("SELECT can_edit_own_name FROM users WHERE mobile = '+989151111111'")
        ).scalar_one() in (False, 0)
    engine.dispose()

    command.downgrade(config, "0018_call_integration")
    columns = {column["name"] for column in inspect(create_engine(database_url)).get_columns("users")}
    assert "can_edit_own_name" not in columns


def test_stage_title_alignment_migration_preserves_and_restores_existing_data(
    monkeypatch,
    tmp_path,
):
    database_path = tmp_path / "stage-title-migration.db"
    database_url = f"sqlite:///{database_path}"
    monkeypatch.setenv("DATABASE_URL", database_url)
    config = alembic_config()
    command.upgrade(config, "0009_incident_unique_cleanup")

    engine = create_engine(database_url)
    old_titles = {
        3: "دریافت DWG و اطلاعات",
        5: "مأموریت",
        6: "آمادگی در محل",
        7: "برداشت Floor",
        8: "چند Floor",
        10: "پردازش در پلتفرم اصلی",
        11: "اطلاع‌رسانی",
        12: "آموزش مالک",
    }
    new_titles = {
        3: "دریافت DWG و اطلاعات طبقات",
        5: "برنامه‌ریزی و تخصیص مأموریت",
        6: "آمادگی قبل از برداشت",
        7: "اجرای برداشت طبقات",
        8: "کنترل نتیجه چندطبقه",
        10: "کنترل پردازش در پلتفرم اصلی",
        11: "اطلاع‌رسانی آماده‌شدن بازدید",
        12: "آموزش اولیه مالک",
    }
    with engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO pilots "
                "(id, code, pilot_year, sequence, project_number, "
                "project_system_name, display_name, status, current_stage, "
                "created_at, updated_at) VALUES "
                "(1, 'PIL-1405-001', 1405, 1, 1, 'project-1', "
                "'Migration pilot', 'operations', 12, "
                "'2026-08-01 00:00:00', '2026-08-01 00:00:00')"
            )
        )
        connection.execute(
            text(
                "INSERT INTO pilot_stages "
                "(id, pilot_id, number, title, status, latest_version, "
                "created_at, updated_at) VALUES "
                "(:id, 1, :number, :title, 'locked', 0, "
                "'2026-08-01 00:00:00', '2026-08-01 00:00:00')"
            ),
            [
                {"id": index, "number": number, "title": title}
                for index, (number, title) in enumerate(old_titles.items(), start=1)
            ],
        )
    engine.dispose()

    command.upgrade(config, "head")
    engine = create_engine(database_url)
    with engine.connect() as connection:
        upgraded = dict(
            connection.execute(
                text("SELECT number, title FROM pilot_stages ORDER BY number")
            ).all()
        )
    assert upgraded == new_titles
    engine.dispose()

    command.downgrade(config, "0009_incident_unique_cleanup")
    engine = create_engine(database_url)
    with engine.connect() as connection:
        downgraded = dict(
            connection.execute(
                text("SELECT number, title FROM pilot_stages ORDER BY number")
            ).all()
        )
    assert downgraded == old_titles
    engine.dispose()


def test_stage_13_19_titles_and_g5_alignment_are_reversible(
    monkeypatch,
    tmp_path,
):
    database_path = tmp_path / "stage-13-19-g5-migration.db"
    database_url = f"sqlite:///{database_path}"
    monkeypatch.setenv("DATABASE_URL", database_url)
    config = alembic_config()
    command.upgrade(config, "0011_optional_stage17_proposal_pdf")

    old_titles = {
        13: "موفقیت مشتری",
        14: "ادامه برداشت",
        15: "ارزیابی",
        16: "جلسه جمع‌بندی",
        17: "پیشنهاد تجاری",
        18: "پیگیری",
        19: "قرارداد یا بستن",
    }
    new_titles = {
        13: "پیگیری موفقیت مشتری",
        14: "ادامه برداشت‌های پایلوت",
        15: "ارزیابی موفقیت پایلوت",
        16: "جلسه جمع‌بندی با مالک",
        17: "تهیه و ارائه پیشنهاد تجاری",
        18: "پیگیری تا تصمیم و عقد قرارداد",
        19: "تبدیل پایلوت به قرارداد یا بستن پرونده",
    }
    engine = create_engine(database_url)
    with engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO pilots "
                "(id, code, pilot_year, sequence, project_number, "
                "project_system_name, display_name, status, current_stage, "
                "created_at, updated_at) VALUES "
                "(1, 'PIL-1405-001', 1405, 1, 1, 'project-1', "
                "'Migration pilot', 'evaluating', 16, "
                "'2026-08-01 00:00:00', '2026-08-01 00:00:00')"
            )
        )
        connection.execute(
            text(
                "INSERT INTO pilot_stages "
                "(id, pilot_id, number, title, status, latest_version, "
                "approved_at, created_at, updated_at) VALUES "
                "(:id, 1, :number, :title, :status, 1, :approved_at, "
                "'2026-08-01 00:00:00', '2026-08-01 00:00:00')"
            ),
            [
                {
                    "id": index,
                    "number": number,
                    "title": title,
                    "status": "approved" if number == 15 else "open",
                    "approved_at": (
                        "2026-08-01 01:00:00" if number == 15 else None
                    ),
                }
                for index, (number, title) in enumerate(old_titles.items(), start=1)
            ],
        )
        connection.execute(
            text(
                "INSERT INTO pilot_gates "
                "(pilot_id, code, title, after_stage, status, passed_at) "
                "VALUES (1, 'G5', 'تجاری', 16, 'locked', NULL)"
            )
        )
    engine.dispose()

    command.upgrade(config, "head")
    engine = create_engine(database_url)
    with engine.connect() as connection:
        upgraded_titles = dict(
            connection.execute(
                text("SELECT number, title FROM pilot_stages ORDER BY number")
            ).all()
        )
        upgraded_gate = connection.execute(
            text(
                "SELECT after_stage, status, passed_at FROM pilot_gates "
                "WHERE code = 'G5'"
            )
        ).one()
    assert upgraded_titles == new_titles
    assert upgraded_gate.after_stage == 15
    assert upgraded_gate.status == "passed"
    assert upgraded_gate.passed_at is not None
    engine.dispose()

    command.downgrade(config, "0011_optional_stage17_proposal_pdf")
    engine = create_engine(database_url)
    with engine.connect() as connection:
        downgraded_titles = dict(
            connection.execute(
                text("SELECT number, title FROM pilot_stages ORDER BY number")
            ).all()
        )
        downgraded_gate = connection.execute(
            text(
                "SELECT after_stage, status, passed_at FROM pilot_gates "
                "WHERE code = 'G5'"
            )
        ).one()
    assert downgraded_titles == old_titles
    assert downgraded_gate.after_stage == 16
    assert downgraded_gate.status == "locked"
    assert downgraded_gate.passed_at is None
    engine.dispose()


def test_call_permission_cleanup_removes_orphans_and_spares_everything_else(
    monkeypatch,
    tmp_path,
):
    database_path = tmp_path / "remove-call-permissions.db"
    database_url = f"sqlite:///{database_path}"
    monkeypatch.setenv("DATABASE_URL", database_url)
    config = alembic_config()

    command.upgrade(config, "0021_remove_call_integration")
    engine = create_engine(database_url)

    # Rebuild the production shape: the six orphans plus a grant that survives a
    # reseed because it belongs to a custom (non-system) role.
    with engine.begin() as connection:
        for code, sensitive in (
            ("calls.read", 0),
            ("calls.initiate", 0),
            ("calls.record_outcome", 0),
            ("calls.retry", 0),
            ("calls.recording.read", 1),
            ("calls.override", 1),
        ):
            connection.execute(
                text(
                    "INSERT INTO permissions (code, group_name, description, is_sensitive)"
                    " VALUES (:code, 'Calls', 'legacy', :sensitive)"
                ),
                {"code": code, "sensitive": sensitive},
            )
        connection.execute(
            text(
                "INSERT INTO permissions (code, group_name, description, is_sensitive)"
                " VALUES ('pilots.read', 'Pilots', 'keep me', 0)"
            )
        )
        connection.execute(
            text(
                "INSERT INTO roles (name, display_name, is_system, is_active,"
                " created_at, updated_at) VALUES ('legacy_call_desk', 'legacy',"
                " 0, 1, '2026-01-01', '2026-01-01')"
            )
        )
        connection.execute(
            text(
                "INSERT INTO role_permissions (role_id, permission_id, assigned_at)"
                " SELECT r.id, p.id, '2026-01-01' FROM roles r, permissions p"
                " WHERE r.name = 'legacy_call_desk' AND p.code LIKE 'calls.%'"
            )
        )

    with engine.connect() as connection:
        assert connection.execute(
            text("SELECT COUNT(*) FROM permissions WHERE code LIKE 'calls.%'")
        ).scalar() == 6
        assert connection.execute(
            text(
                "SELECT COUNT(*) FROM role_permissions rp JOIN permissions p"
                " ON p.id = rp.permission_id WHERE p.code LIKE 'calls.%'"
            )
        ).scalar() == 6

    command.upgrade(config, "0022_remove_call_permissions")
    engine = create_engine(database_url)
    with engine.connect() as connection:
        assert connection.execute(
            text("SELECT COUNT(*) FROM permissions WHERE code LIKE 'calls.%'")
        ).scalar() == 0
        assert connection.execute(
            text(
                "SELECT COUNT(*) FROM role_permissions rp JOIN permissions p"
                " ON p.id = rp.permission_id WHERE p.code LIKE 'calls.%'"
            )
        ).scalar() == 0
        # Untouched: the unrelated permission and the custom role itself.
        assert connection.execute(
            text("SELECT COUNT(*) FROM permissions WHERE code = 'pilots.read'")
        ).scalar() == 1
        assert connection.execute(
            text("SELECT COUNT(*) FROM roles WHERE name = 'legacy_call_desk'")
        ).scalar() == 1

    # Downgrade restores the rows only, never the grants.
    command.downgrade(config, "0021_remove_call_integration")
    engine = create_engine(database_url)
    with engine.connect() as connection:
        assert connection.execute(
            text("SELECT COUNT(*) FROM permissions WHERE code LIKE 'calls.%'")
        ).scalar() == 6
        assert connection.execute(
            text(
                "SELECT COUNT(*) FROM role_permissions rp JOIN permissions p"
                " ON p.id = rp.permission_id WHERE p.code LIKE 'calls.%'"
            )
        ).scalar() == 0
    engine.dispose()
