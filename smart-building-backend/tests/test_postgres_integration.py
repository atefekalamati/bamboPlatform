"""Live PostgreSQL schema and persistence checks used by Backend CI."""

import os
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Barrier
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.engine import make_url
from sqlalchemy.pool import NullPool

import app.database as database
import app.models  # noqa: F401
from app.exceptions import SecurityError, WorkflowError
from app.models import (
    AuditLog,
    AuthSession,
    FormF04,
    OtpRequest,
    Pilot,
    Role,
    StageApproval,
    StageSubmission,
    User,
)
from app.schemas.experience import FormF04Patch
from app.schemas.workflow import PilotCreate, StageReject
from app.services.experience import patch_f04
from app.services.security import (
    AuthContext,
    request_otp,
    refresh_session,
    revoke_session,
    seed_security_data,
    verify_otp,
)
from app.services.workflow import approve_stage, create_pilot, reject_stage

POSTGRES_SERVER_URL = os.getenv("POSTGRES_TEST_DATABASE_URL")

pytestmark = pytest.mark.skipif(
    not POSTGRES_SERVER_URL,
    reason="POSTGRES_TEST_DATABASE_URL is not configured",
)


BACKEND_ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture(scope="session")
def postgres_database_url() -> str:
    """A throwaway database of its own, migrated to head and dropped after.

    ``POSTGRES_TEST_DATABASE_URL`` names a server, not the database these tests
    run against: only its connection details are borrowed. Sharing one database
    across runs left pilots behind, so a second run numbered the next pilot
    ``PIL-1499-002`` and the assertions — written for a clean sequence — failed
    on data, not on behaviour.

    Creating the database here rather than reusing whatever the caller points at
    also keeps a development database safe from a mistyped environment variable.
    """
    server_url = make_url(POSTGRES_SERVER_URL)
    database_name = f"bambo_test_{uuid4().hex[:12]}"
    # CREATE/DROP DATABASE cannot run inside a transaction.
    maintenance = create_engine(
        server_url.set(database="postgres"),
        isolation_level="AUTOCOMMIT",
        poolclass=NullPool,
    )
    test_url = server_url.set(database=database_name)

    with maintenance.connect() as connection:
        connection.execute(text(f'CREATE DATABASE "{database_name}"'))

    previous_database_url = os.environ.get("DATABASE_URL")
    try:
        # Migrate through Alembic so the schema under test is the real one,
        # resolved from the scripts rather than from Base.metadata.
        os.environ["DATABASE_URL"] = test_url.render_as_string(hide_password=False)
        command.upgrade(Config(str(BACKEND_ROOT / "alembic.ini")), "head")
        yield os.environ["DATABASE_URL"]
    finally:
        if previous_database_url is None:
            os.environ.pop("DATABASE_URL", None)
        else:
            os.environ["DATABASE_URL"] = previous_database_url

        # Release the app engine's pool; an open connection blocks DROP DATABASE.
        if database.engine is not None:
            database.engine.dispose()
            database.engine = None

        with maintenance.connect() as connection:
            connection.execute(
                text(
                    "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
                    "WHERE datname = :name AND pid <> pg_backend_pid()"
                ),
                {"name": database_name},
            )
            connection.execute(text(f'DROP DATABASE IF EXISTS "{database_name}"'))
        maintenance.dispose()


@pytest.fixture(autouse=True)
def _bind_app_to_test_database(monkeypatch, postgres_database_url):
    """Point every test in this module at the throwaway database."""
    monkeypatch.setenv("DATABASE_URL", postgres_database_url)


def expected_migration_head() -> str:
    """Resolve the head from the migration scripts, never from a literal.

    A hardcoded revision goes stale on the next migration and fails a schema
    that is actually correct. Reading it from ``ScriptDirectory`` also catches a
    branched history, which would silently leave the database on one of several
    heads.
    """
    config = Config(str(BACKEND_ROOT / "alembic.ini"))
    heads = ScriptDirectory.from_config(config).get_heads()
    assert len(heads) == 1, f"expected exactly one alembic head, found {heads}"
    return heads[0]


def _column_type(inspector, table_name: str, column_name: str):
    return next(
        column["type"]
        for column in inspector.get_columns(table_name)
        if column["name"] == column_name
    )


def test_postgresql_schema_and_persistence(monkeypatch):
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
            == expected_migration_head()
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


def _request_test_otp(mobile: str) -> tuple[str, str]:
    with database.get_session() as db:
        dispatch = request_otp(db, mobile, "127.0.0.1")
        assert dispatch.debug_code is not None
        return dispatch.request.public_id, dispatch.debug_code


def _verify_test_otp(
    barrier: Barrier,
    request_id: str,
    code: str,
) -> tuple[str, int]:
    barrier.wait()
    with database.get_session() as db:
        try:
            token, _, _, _, user = verify_otp(db, request_id, code, "127.0.0.1")
            return token, user.id
        except SecurityError as exc:
            db.rollback()
            return "", exc.status_code


def _logout_test_session(barrier: Barrier, session_id: int) -> None:
    with database.get_session() as db:
        auth_session = db.get(AuthSession, session_id)
        context = AuthContext(user=auth_session.user, session=auth_session)
        barrier.wait()
        revoke_session(db, context)


def _refresh_at_once(barrier: Barrier, refresh_token: str) -> tuple[bool, str]:
    barrier.wait()
    with database.get_session() as db:
        try:
            _, rotated_token, _, _, _ = refresh_session(
                db,
                refresh_token,
                ip_address="127.0.0.1",
                user_agent="postgres-concurrency-test",
            )
            return True, rotated_token
        except SecurityError as exc:
            db.rollback()
            return False, exc.code


def test_postgresql_concurrent_otp_and_rate_limit(monkeypatch):
    monkeypatch.setenv("OTP_RESEND_COOLDOWN_SECONDS", "0")
    monkeypatch.setenv("OTP_MAX_REQUESTS_PER_WINDOW", "3")
    engine = database.get_engine()

    replay_mobile = "+989150001001"
    request_id, code = _request_test_otp(replay_mobile)
    replay_barrier = Barrier(2)
    with ThreadPoolExecutor(max_workers=2) as executor:
        replay_results = list(
            executor.map(
                lambda _: _verify_test_otp(replay_barrier, request_id, code),
                range(2),
            )
        )
    assert sorted(result[1] for result in replay_results if not result[0]) == [400]
    assert len([result for result in replay_results if result[0]]) == 1

    parallel_mobile = "+989150001002"
    first_request = _request_test_otp(parallel_mobile)
    second_request = _request_test_otp(parallel_mobile)
    login_barrier = Barrier(2)
    with ThreadPoolExecutor(max_workers=2) as executor:
        login_results = list(
            executor.map(
                lambda credentials: _verify_test_otp(
                    login_barrier,
                    credentials[0],
                    credentials[1],
                ),
                (first_request, second_request),
            )
        )
    assert all(token for token, _ in login_results)
    assert login_results[0][1] == login_results[1][1]
    assert login_results[0][0] != login_results[1][0]

    limited_mobile = "+989150001003"
    rate_barrier = Barrier(4)

    def request_at_once(_: int) -> int:
        rate_barrier.wait()
        with database.get_session() as db:
            try:
                request_otp(db, limited_mobile, "192.0.2.10")
                return 200
            except SecurityError as exc:
                db.rollback()
                return exc.status_code

    with ThreadPoolExecutor(max_workers=4) as executor:
        rate_results = list(executor.map(request_at_once, range(4)))
    assert sorted(rate_results) == [200, 200, 200, 429]

    with database.get_session() as db:
        replay_user = db.query(User).filter(User.mobile == replay_mobile).one()
        parallel_user = db.query(User).filter(User.mobile == parallel_mobile).one()
        assert db.query(AuthSession).filter(AuthSession.user_id == replay_user.id).count() == 1
        assert db.query(AuthSession).filter(AuthSession.user_id == parallel_user.id).count() == 2
        assert db.query(User).filter(User.mobile == parallel_mobile).count() == 1
        assert db.query(OtpRequest).filter(OtpRequest.mobile == limited_mobile).count() == 3
        logout_session_id = (
            db.query(AuthSession.id)
            .filter(AuthSession.user_id == parallel_user.id)
            .order_by(AuthSession.id)
            .first()[0]
        )

    logout_barrier = Barrier(2)
    with ThreadPoolExecutor(max_workers=2) as executor:
        list(
            executor.map(
                lambda _: _logout_test_session(logout_barrier, logout_session_id),
                range(2),
            )
        )
    with database.get_session() as db:
        logged_out = db.get(AuthSession, logout_session_id)
        assert logged_out.revoked_at is not None
        assert (
            db.query(AuditLog)
            .filter(
                AuditLog.action == "auth.logout",
                AuditLog.session_id == logout_session_id,
            )
            .count()
            == 1
        )

    engine.dispose()


def test_postgresql_concurrent_refresh_has_one_winner_and_revokes_replay_family(
    monkeypatch,
):
    engine = database.get_engine()
    mobile = "+989150001004"
    request_id, code = _request_test_otp(mobile)
    with database.get_session() as db:
        _, refresh_token, _, _, user = verify_otp(
            db,
            request_id,
            code,
            "127.0.0.1",
        )
        user_id = user.id

    barrier = Barrier(2)
    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(
            executor.map(
                lambda _: _refresh_at_once(barrier, refresh_token),
                range(2),
            )
        )
    successes = [value for succeeded, value in results if succeeded]
    failures = [value for succeeded, value in results if not succeeded]
    assert len(successes) == 1
    assert failures == ["REFRESH_TOKEN_REVOKED"]

    with database.get_session() as db:
        sessions = db.query(AuthSession).filter(AuthSession.user_id == user_id).all()
        assert sessions
        assert all(session.revoked_at is not None for session in sessions)
    engine.dispose()


def _create_submitted_stage_two(pilot_year: int) -> tuple[int, int]:
    with database.get_session() as db:
        pilot = create_pilot(
            db,
            PilotCreate.model_validate(
                {
                    "pilot_year": pilot_year,
                    "owner": {
                        "name": f"Concurrent Owner {pilot_year}",
                        "decision_maker_name": "Decision Maker",
                        "decision_maker_position": "Director",
                        "primary_mobile": f"+9891{pilot_year}00000",
                    },
                    "project": {
                        "name": f"Concurrent project {pilot_year}",
                        "total_floors": 1,
                        "address": "PostgreSQL concurrency test",
                        "progress_stage": "active",
                        "customer_need": "Verify one final decision",
                        "expected_value": "Prevent duplicate transitions",
                    },
                }
            ),
        )
        stage_one, stage_two = pilot.stages[:2]
        stage_one.status = "approved"
        stage_two.status = "submitted"
        stage_two.latest_version = 1
        pilot.current_stage = 2
        submission = StageSubmission(
            stage=stage_two,
            version=1,
            status="submitted",
            form_data={"site_coordinator_phone": "+989150000000"},
            checklist={
                "introduction_completed": True,
                "site_coordinator_registered": True,
                "imaging_consent": True,
                "dwg_consent": True,
                "feedback_consent": True,
                "f01_result_approved": True,
            },
            submitted_by="Concurrent submitter",
        )
        db.add(submission)
        db.commit()
        return pilot.id, stage_two.id


def _decide_stage(
    barrier: Barrier,
    pilot_id: int,
    decision: str,
) -> tuple[str, int]:
    barrier.wait()
    with database.get_session() as db:
        try:
            if decision == "approved":
                approve_stage(db, pilot_id, 2, reviewer="Concurrent reviewer")
            else:
                reject_stage(
                    db,
                    pilot_id,
                    2,
                    StageReject(reason="Concurrent rejection"),
                    reviewer="Concurrent reviewer",
                )
            return decision, 200
        except WorkflowError as exc:
            db.rollback()
            return decision, exc.status_code


@pytest.mark.parametrize(
    ("pilot_year", "decisions"),
    ((1497, ("approved", "approved")), (1498, ("approved", "rejected"))),
)
def test_postgresql_concurrent_stage_decision_accepts_one(
    monkeypatch,
    pilot_year,
    decisions,
):
    engine = database.get_engine()
    pilot_id, stage_id = _create_submitted_stage_two(pilot_year)
    barrier = Barrier(2)
    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(
            executor.map(
                lambda decision: _decide_stage(barrier, pilot_id, decision),
                decisions,
            )
        )
    assert sorted(status for _, status in results) == [200, 409]

    with database.get_session() as db:
        pilot = db.get(Pilot, pilot_id)
        stage = next(item for item in pilot.stages if item.number == 2)
        gate = next(item for item in pilot.gates if item.code == "G1")
        approval = (
            db.query(StageApproval)
            .join(StageSubmission)
            .filter(StageSubmission.stage_id == stage_id)
            .one()
        )
        decision_audits = (
            db.query(AuditLog)
            .filter(
                AuditLog.entity_type == "PilotStage",
                AuditLog.entity_id == str(stage_id),
                AuditLog.action.in_(("stages.approved", "stages.rejected")),
            )
            .all()
        )
        assert len(decision_audits) == 1
        if approval.decision == "approved":
            assert stage.status == "approved"
            assert pilot.current_stage == 3
            assert gate.status == "passed"
        else:
            assert stage.status == "needs_revision"
            assert pilot.current_stage == 2
            assert gate.status == "locked"

    engine.dispose()


def test_postgresql_concurrent_f04_partial_updates_preserve_fields(monkeypatch):
    engine = database.get_engine()
    with database.get_session() as db:
        seed_security_data(db)
        super_admin_role = db.query(Role).filter(Role.name == "super_admin").one()
        actor = User(
            mobile="+989150001100",
            display_name="Concurrent F04 actor",
            roles=[super_admin_role],
        )
        db.add(actor)
        db.flush()
        pilot = create_pilot(
            db,
            PilotCreate.model_validate(
                {
                    "pilot_year": 1496,
                    "owner": {
                        "name": "Concurrent F04 owner",
                        "decision_maker_name": "Decision Maker",
                        "decision_maker_position": "Director",
                        "primary_mobile": "+989150001101",
                    },
                    "project": {
                        "name": "Concurrent F04 project",
                        "total_floors": 1,
                        "address": "PostgreSQL concurrency test",
                        "progress_stage": "active",
                        "customer_need": "Preserve independent draft fields",
                        "expected_value": "Prevent duplicate F04 rows",
                    },
                }
            ),
            actor_user_id=actor.id,
        )
        pilot.current_stage = 12
        db.commit()
        pilot_id = pilot.id
        actor_id = actor.id

    barrier = Barrier(2)
    payloads = (
        FormF04Patch(owner_logged_in=True),
        FormF04Patch(project_opened=True),
    )

    def update_at_once(payload: FormF04Patch) -> None:
        barrier.wait()
        with database.get_session() as db:
            patch_f04(
                db,
                pilot_id,
                payload,
                actor_user_id=actor_id,
                session_id=None,
            )

    with ThreadPoolExecutor(max_workers=2) as executor:
        list(executor.map(update_at_once, payloads))

    with database.get_session() as db:
        forms = db.query(FormF04).filter(FormF04.pilot_id == pilot_id).all()
        assert len(forms) == 1
        assert forms[0].owner_logged_in is True
        assert forms[0].project_opened is True

    engine.dispose()


def test_postgresql_incident_list_indexes_and_query_plan(monkeypatch):
    engine = database.get_engine()
    inspector = inspect(engine)
    index_names = {
        index["name"] for index in inspector.get_indexes("incidents")
    }
    assert {
        "ix_incidents_pilot_id",
        "ix_incidents_status",
        "ix_incidents_severity",
        "ix_incidents_occurred_at",
        "ix_incidents_response_due_at",
        "ix_incidents_correction_due_at",
    }.issubset(index_names)

    with engine.connect() as connection:
        plan = connection.execute(
            text(
                "EXPLAIN SELECT i.id FROM incidents AS i "
                "JOIN pilots AS p ON p.id = i.pilot_id "
                "WHERE i.status = 'open' AND i.severity = 'critical' "
                "ORDER BY i.occurred_at DESC LIMIT 20"
            )
        ).all()
    assert plan
    engine.dispose()
