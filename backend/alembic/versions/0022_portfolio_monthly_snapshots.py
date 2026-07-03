"""portfolio_monthly_snapshots 테이블 생성 (SPEC-STOCK-035)

Revision ID: 0022
Revises: 0021
Create Date: 2026-06-24

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0022"
down_revision: str | None = "0021"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """portfolio_monthly_snapshots 테이블 및 인덱스 생성."""
    op.create_table(
        "portfolio_monthly_snapshots",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("portfolio_id", sa.Integer(), nullable=False),
        # month: "YYYY-MM" 7자 문자열 — 월별 집계 키
        sa.Column("month", sa.String(7), nullable=False),
        sa.Column("total_value_krw", sa.Float(), nullable=False),
        # total_return_pct: 기간 비교 불가 시 NULL 허용
        sa.Column("total_return_pct", sa.Float(), nullable=True),
        sa.Column("holding_count", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        # 외래 키 — portfolios 삭제 시 스냅샷도 CASCADE 삭제
        sa.ForeignKeyConstraint(["portfolio_id"], ["portfolios.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        # (portfolio_id, month) 복합 UNIQUE — 월별 1개 스냅샷만 허용
        sa.UniqueConstraint("portfolio_id", "month", name="uq_snapshot_portfolio_month"),
    )
    # 기본 ID 인덱스
    op.create_index(
        "ix_portfolio_monthly_snapshots_id",
        "portfolio_monthly_snapshots",
        ["id"],
    )
    # 포트폴리오별 스냅샷 조회 최적화
    op.create_index(
        "ix_portfolio_monthly_snapshots_portfolio_id",
        "portfolio_monthly_snapshots",
        ["portfolio_id"],
    )


def downgrade() -> None:
    """portfolio_monthly_snapshots 테이블 및 인덱스 제거."""
    op.drop_index("ix_portfolio_monthly_snapshots_portfolio_id", table_name="portfolio_monthly_snapshots")
    op.drop_index("ix_portfolio_monthly_snapshots_id", table_name="portfolio_monthly_snapshots")
    op.drop_table("portfolio_monthly_snapshots")
