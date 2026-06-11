"""backtest_runs 테이블에 universe_size, top_n 컬럼 추가 (SPEC-STOCK-012 M1)

Revision ID: 0013
Revises: 0012
Create Date: 2026-06-11
"""

import sqlalchemy as sa
from alembic import op

revision = "0013"
down_revision = "0012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """backtest_runs 테이블에 universe_size, top_n 컬럼 추가."""
    op.add_column(
        "backtest_runs",
        sa.Column("universe_size", sa.Integer(), nullable=True),
    )
    op.add_column(
        "backtest_runs",
        sa.Column("top_n", sa.Integer(), nullable=True),
    )


def downgrade() -> None:
    """backtest_runs 테이블에서 universe_size, top_n 컬럼 제거."""
    op.drop_column("backtest_runs", "top_n")
    op.drop_column("backtest_runs", "universe_size")
