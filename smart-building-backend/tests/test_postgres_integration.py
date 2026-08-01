"""Live PostgreSQL schema and persistence checks used by Backend CI."""

import os
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import pytest
from sqlalchemy import inspect, text
from sqlalchemy.dialects.postgresql import JSONB

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
    revoke_session,
    seed_security_data,
    verify_otp,
)
from app.services.workflow import approve_stage, create_pilot, reject_stage

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
            == "0012_stage_13_19_g5_alignment"
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
            token, _, user = verify_otp(db, request_id, code, "127.0.0.1")
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


def test_postgresql_concurrent_otp_and_rate_limit(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", POSTGRES_TEST_DATABASE_URL)
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
    monkeypatch.setenv("DATABASE_URL", POSTGRES_TEST_DATABASE_URL)
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
    monkeypatch.setenv("DATABASE_URL", POSTGRES_TEST_DATABASE_URL)
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
