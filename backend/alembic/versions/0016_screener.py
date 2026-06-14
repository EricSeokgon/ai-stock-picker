"""stock_fundamentals + screener_presets 테이블 (SPEC-STOCK-018)

Revision ID: 0016
Revises: 0015
Create Date: 2026-06-15

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0016"
down_revision: str = "0015"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # stock_fundamentals 테이블 생성
    op.create_table(
        "stock_fundamentals",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("krx_code", sa.String(length=10), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=True),
        sa.Column("sector", sa.String(length=100), nullable=True),
        sa.Column("current_price", sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column("change_pct", sa.Numeric(precision=8, scale=4), nullable=True),
        sa.Column("per", sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column("pbr", sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column("roe", sa.Numeric(precision=8, scale=4), nullable=True),
        sa.Column("market_cap", sa.BigInteger(), nullable=True),
        sa.Column("dividend_yield", sa.Numeric(precision=8, scale=4), nullable=True),
        sa.Column("week52_high", sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column("week52_low", sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column("price_vs_52w_pct", sa.Numeric(precision=8, scale=4), nullable=True),
        sa.Column("snapshot_date", sa.Date(), nullable=False),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "krx_code", "snapshot_date", name="uq_fundamentals_code_date"
        ),
    )
    op.create_index(
        "ix_fundamentals_snapshot_date",
        "stock_fundamentals",
        ["snapshot_date"],
    )

    # screener_presets 테이블 생성
    op.create_table(
        "screener_presets",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("criteria", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "user_id", "name", name="uq_screener_preset_user_name"
        ),
    )


def downgrade() -> None:
    op.drop_table("screener_presets")
    op.drop_index("ix_fundamentals_snapshot_date", table_name="stock_fundamentals")
    op.drop_table("stock_fundamentals")
