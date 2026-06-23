"""rebalancing_plans 테이블 생성 (SPEC-STOCK-032)

Revision ID: 0021
Revises: 0020
Create Date: 2026-06-23

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0021"
down_revision: str | None = "0020"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """rebalancing_plans 테이블 및 인덱스 생성."""
    op.create_table(
        "rebalancing_plans",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("portfolio_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("budget", sa.Float(), nullable=False),
        sa.Column("total_buy_amount", sa.Float(), nullable=False, server_default=sa.text("0")),
        sa.Column("total_sell_amount", sa.Float(), nullable=False, server_default=sa.text("0")),
        sa.Column("total_commission", sa.Float(), nullable=False, server_default=sa.text("0")),
        # 주문 목록 JSON 직렬화 (SQLite 호환, JSONB 미사용)
        sa.Column("orders_json", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        # 외래 키
        sa.ForeignKeyConstraint(["portfolio_id"], ["portfolios.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    # 포트폴리오별 최신 리밸런싱 계획 조회 최적화
    op.create_index(
        "ix_rebalancing_plans_portfolio_created",
        "rebalancing_plans",
        ["portfolio_id", "created_at"],
    )


def downgrade() -> None:
    """rebalancing_plans 테이블 및 인덱스 제거."""
    op.drop_index("ix_rebalancing_plans_portfolio_created", table_name="rebalancing_plans")
    op.drop_table("rebalancing_plans")
