"""backtest_runs, backtest_daily_results 테이블 추가 마이그레이션

Revision ID: 0005
Revises: 0004
Create Date: 2026-06-09
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# 리비전 식별자
revision: str = "0005"
down_revision: Union[str, None] = "0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """backtest_runs, backtest_daily_results 테이블 생성"""
    op.create_table(
        "backtest_runs",
        sa.Column("id", sa.Integer(), nullable=False, autoincrement=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("strategy", sa.String(length=50), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=False),
        sa.Column(
            "status",
            sa.String(length=20),
            nullable=False,
            server_default=sa.text("'pending'"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], ondelete="CASCADE", name="fk_backtest_runs_user_id"
        ),
    )
    op.create_index("ix_backtest_runs_user_id", "backtest_runs", ["user_id"])
    op.create_index("ix_backtest_runs_status", "backtest_runs", ["status"])

    op.create_table(
        "backtest_daily_results",
        sa.Column("id", sa.Integer(), nullable=False, autoincrement=True),
        sa.Column("run_id", sa.Integer(), nullable=False),
        sa.Column("trade_date", sa.Date(), nullable=False),
        sa.Column("krx_code", sa.String(length=10), nullable=False),
        sa.Column("signal", sa.String(length=10), nullable=False),
        sa.Column("price", sa.Numeric(10, 2), nullable=False),
        sa.Column("return_pct", sa.Numeric(8, 4), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["run_id"],
            ["backtest_runs.id"],
            ondelete="CASCADE",
            name="fk_daily_results_run_id",
        ),
    )
    op.create_index("ix_backtest_daily_results_run_id", "backtest_daily_results", ["run_id"])
    op.create_index(
        "ix_backtest_daily_results_trade_date", "backtest_daily_results", ["trade_date"]
    )


def downgrade() -> None:
    """backtest_runs, backtest_daily_results 테이블 롤백"""
    op.drop_index("ix_backtest_daily_results_trade_date", table_name="backtest_daily_results")
    op.drop_index("ix_backtest_daily_results_run_id", table_name="backtest_daily_results")
    op.drop_table("backtest_daily_results")
    op.drop_index("ix_backtest_runs_status", table_name="backtest_runs")
    op.drop_index("ix_backtest_runs_user_id", table_name="backtest_runs")
    op.drop_table("backtest_runs")
