"""Align persisted Stage 1-12 titles with the finalized frontend.

Revision ID: 0010_stage_1_12_alignment
Revises: 0009_incident_unique_cleanup
Create Date: 2026-08-01
"""

from typing import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "0010_stage_1_12_alignment"
down_revision: str | None = "0009_incident_unique_cleanup"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


STAGE_TITLE_CHANGES = (
    (3, "دریافت DWG و اطلاعات", "دریافت DWG و اطلاعات طبقات"),
    (5, "مأموریت", "برنامه‌ریزی و تخصیص مأموریت"),
    (6, "آمادگی در محل", "آمادگی قبل از برداشت"),
    (7, "برداشت Floor", "اجرای برداشت طبقات"),
    (8, "چند Floor", "کنترل نتیجه چندطبقه"),
    (10, "پردازش در پلتفرم اصلی", "کنترل پردازش در پلتفرم اصلی"),
    (11, "اطلاع‌رسانی", "اطلاع‌رسانی آماده‌شدن بازدید"),
    (12, "آموزش مالک", "آموزش اولیه مالک"),
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


def upgrade() -> None:
    # Match only the known previous system title so unexpected custom data is
    # preserved instead of being overwritten by this data migration.
    _replace_titles(1, 2)


def downgrade() -> None:
    _replace_titles(2, 1)
