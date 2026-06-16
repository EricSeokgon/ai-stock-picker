"""notification_preferences 테이블 — 사용자별 알림 채널·유형 ON/OFF 설정 (SPEC-STOCK-025)

Revision ID: 0018
Revises: 0017
Create Date: 2026-06-16

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0018"
down_revision: str | None = "0017"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """notification_preferences 테이블 생성 및 UNIQUE 인덱스 추가."""
    op.create_table(
        "notification_preferences",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("alert_type", sa.String(20), nullable=False),
        sa.Column("email_enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("telegram_enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "alert_type", name="uq_pref_user_type"),
    )
    # 사용자별 설정 조회 최적화 인덱스
    op.create_index(
        "ix_notification_preferences_user_id",
        "notification_preferences",
        ["user_id"],
    )


def downgrade() -> None:
    """notification_preferences 테이블 삭제."""
    op.drop_index("ix_notification_preferences_user_id", table_name="notification_preferences")
    op.drop_table("notification_preferences")
