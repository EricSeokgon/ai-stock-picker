"""portfolio_alerts 테이블 생성 (SPEC-STOCK-031)

Revision ID: 0020
Revises: 0019
Create Date: 2026-06-23

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0020"
down_revision: str | None = "0019"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """portfolio_alerts 테이블 및 인덱스 생성."""
    op.create_table(
        "portfolio_alerts",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("portfolio_id", sa.Integer(), nullable=False),
        # 알림 유형: portfolio_target_return | portfolio_mdd_breach
        sa.Column("alert_type", sa.String(length=30), nullable=False),
        # 목표 수익률(%) 또는 MDD 임계값(%) — 음수 가능
        sa.Column("condition_value", sa.Float(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("is_triggered", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column(
            "triggered_at",
            sa.TIMESTAMP(timezone=True),
            nullable=True,
        ),
        sa.Column("triggered_message", sa.String(length=500), nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        # 외래 키
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["portfolio_id"], ["portfolios.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        # 동일 (user, portfolio, alert_type) 중복 방지 (REQ-PAL-008)
        sa.UniqueConstraint(
            "user_id", "portfolio_id", "alert_type",
            name="uq_portfolio_alert_user_pf_type",
        ),
    )
    # 활성 알림 조회 최적화 인덱스
    op.create_index(
        "ix_portfolio_alerts_user_active",
        "portfolio_alerts",
        ["user_id", "is_active"],
    )


def downgrade() -> None:
    """portfolio_alerts 테이블 및 인덱스 제거."""
    op.drop_index("ix_portfolio_alerts_user_active", table_name="portfolio_alerts")
    op.drop_table("portfolio_alerts")
