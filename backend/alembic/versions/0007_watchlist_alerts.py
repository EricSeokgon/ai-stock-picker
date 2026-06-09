"""watchlist_alerts 테이블 추가 마이그레이션

Revision ID: 0007
Revises: 0006
Create Date: 2026-06-09
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# 리비전 식별자
revision: str = "0007"
down_revision: Union[str, None] = "0006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """watchlist_alerts 테이블 생성"""
    op.create_table(
        "watchlist_alerts",
        sa.Column("id", sa.Integer(), nullable=False, autoincrement=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("krx_code", sa.String(length=10), nullable=False),
        sa.Column("target_price", sa.Float(), nullable=False),
        # direction: "above" (이상) 또는 "below" (이하)
        sa.Column("direction", sa.String(length=5), nullable=False),
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
        sa.Column("triggered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            ondelete="CASCADE",
            name="fk_watchlist_alerts_user_id",
        ),
    )
    op.create_index("ix_watchlist_alerts_user_id", "watchlist_alerts", ["user_id"])
    op.create_index(
        "ix_watchlist_alerts_active",
        "watchlist_alerts",
        ["is_active", "user_id"],
    )


def downgrade() -> None:
    """watchlist_alerts 테이블 롤백"""
    op.drop_index("ix_watchlist_alerts_active", table_name="watchlist_alerts")
    op.drop_index("ix_watchlist_alerts_user_id", table_name="watchlist_alerts")
    op.drop_table("watchlist_alerts")
