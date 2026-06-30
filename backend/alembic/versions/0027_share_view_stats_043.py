"""share_view_stats 테이블 추가 (SPEC-STOCK-043)

포트폴리오 공유 일별 조회수 통계 테이블.
ON CONFLICT DO UPDATE upsert로 KST 기준 날짜별 view_count 집계.

Revision ID: 0027
Revises: 0026
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

# revision identifiers
revision = "0027"
down_revision = "0026"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "share_view_stats",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column(
            "share_id",
            sa.Integer,
            sa.ForeignKey("portfolio_shares.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("stat_date", sa.Date, nullable=False),
        sa.Column("view_count", sa.Integer, nullable=False, server_default="1"),
    )
    op.create_unique_constraint(
        "uq_share_view_stats_share_date",
        "share_view_stats",
        ["share_id", "stat_date"],
    )
    op.create_index(
        "ix_share_view_stats_share_id_date",
        "share_view_stats",
        ["share_id", "stat_date"],
    )


def downgrade() -> None:
    op.drop_index("ix_share_view_stats_share_id_date", table_name="share_view_stats")
    op.drop_constraint("uq_share_view_stats_share_date", "share_view_stats", type_="unique")
    op.drop_table("share_view_stats")
