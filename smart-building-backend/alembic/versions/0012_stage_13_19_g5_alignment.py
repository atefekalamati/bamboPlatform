"""Align Stage 13-19 titles and move G5 after Stage 15.

Revision ID: 0012_stage_13_19_g5_alignment
Revises: 0011_optional_stage17_proposal_pdf
Create Date: 2026-08-01
"""

from typing import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "0012_stage_13_19_g5_alignment"
down_revision: str | None = "0011_optional_stage17_proposal_pdf"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


STAGE_TITLE_CHANGES = (
    (13, "موفقیت مشتری", "پیگیری موفقیت مشتری"),
    (14, "ادامه برداشت", "ادامه برداشت‌های پایلوت"),
    (15, "ارزیابی", "ارزیابی موفقیت پایلوت"),
    (16, "جلسه جمع‌بندی", "جلسه جمع‌بندی با مالک"),
    (17, "پیشنهاد تجاری", "تهیه و ارائه پیشنهاد تجاری"),
    (18, "پیگیری", "پیگیری تا تصمیم و عقد قرارداد"),
    (19, "قرارداد یا بستن", "تبدیل پایلوت به قرارداد یا بستن پرونده"),
)


def _replace_titles(source_index: int, target_index: int) -> None:
    pilot_stages = sa.table(
        "pilot_stages",
        sa.column("number", sa.Integer()),
        sa.column("title", sa.String()),
    )
    for stage_number, old_title, new_title in STAGE_TITLE_CHANGES:
        titles = (stage_number, old_title, new_title)
        op.execute(
            pilot_stages.update()
            .where(pilot_stages.c.number == stage_number)
            .where(pilot_stages.c.title == titles[source_index])
            .values(title=titles[target_index])
        )


def _align_g5(*, after_stage: int, decision_stage: int) -> None:
    op.get_bind().execute(
        sa.text(
            "UPDATE pilot_gates AS gate "
            "SET after_stage = :after_stage, "
            "status = CASE WHEN EXISTS ("
            "SELECT 1 FROM pilot_stages AS stage "
            "WHERE stage.pilot_id = gate.pilot_id "
            "AND stage.number = :decision_stage "
            "AND stage.status = 'approved'"
            ") THEN 'passed' ELSE 'locked' END, "
            "passed_at = ("
            "SELECT CASE WHEN stage.status = 'approved' "
            "THEN stage.approved_at ELSE NULL END "
            "FROM pilot_stages AS stage "
            "WHERE stage.pilot_id = gate.pilot_id "
            "AND stage.number = :decision_stage"
            ") "
            "WHERE gate.code = 'G5'"
        ),
        {"after_stage": after_stage, "decision_stage": decision_stage},
    )


def upgrade() -> None:
    # Only known system titles are replaced; unexpected customized titles are
    # retained. Existing G5 state is recalculated from the newly authoritative
    # Stage 15 decision so partially completed pilots remain consistent.
    _replace_titles(1, 2)
    _align_g5(after_stage=15, decision_stage=15)


def downgrade() -> None:
    _align_g5(after_stage=16, decision_stage=16)
    _replace_titles(2, 1)
