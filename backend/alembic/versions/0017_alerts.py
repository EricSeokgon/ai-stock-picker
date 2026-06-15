"""alerts 테이블 — 일반 목표가·급등락 알림 (SPEC-STOCK-020)

Revision ID: 0017
Revises: 0016
Create Date: 2026-06-15

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0017"
down_revision: str | None = "0016"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "alerts",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("krx_code", sa.String(length=10), nullable=False),
        sa.Column("stock_name", sa.String(length=100), nullable=True),
        # target_price | surge_drop | ex_dividend
        sa.Column("alert_type", sa.String(length=20), nullable=False),
        # 목표가 또는 급등락 임계값 (%)
        sa.Column("condition_value", sa.Float(), nullable=False),
        # above | below | either
        sa.Column("condition_direction", sa.String(length=8), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("is_triggered", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("triggered_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("triggered_message", sa.String(length=500), nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_alerts_user_active",
        "alerts",
        ["user_id", "is_active"],
    )


def downgrade() -> None:
    op.drop_index("ix_alerts_user_active", table_name="alerts")
    op.drop_table("alerts")
