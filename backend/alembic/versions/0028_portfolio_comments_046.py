"""portfolio_comments 테이블 생성 (SPEC-STOCK-046)

Revision ID: 0028
Revises: 0027
Create Date: 2026-07-01
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import TIMESTAMPTZ

# revision identifiers, used by Alembic.
revision = "0028"
down_revision = "0027"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """portfolio_comments 테이블 생성 및 인덱스 추가"""
    op.create_table(
        "portfolio_comments",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("share_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("content", sa.String(500), nullable=False),
        sa.Column(
            "created_at",
            TIMESTAMPTZ(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["share_id"],
            ["portfolio_shares.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    # (share_id, created_at) 복합 인덱스 — 최신순 댓글 조회 최적화
    op.create_index(
        "ix_portfolio_comments_share_created",
        "portfolio_comments",
        ["share_id", "created_at"],
    )
    # user_id 단일 인덱스 — 사용자별 댓글 조회
    op.create_index(
        "ix_portfolio_comments_user_id",
        "portfolio_comments",
        ["user_id"],
    )


def downgrade() -> None:
    """portfolio_comments 테이블 및 인덱스 제거"""
    op.drop_index("ix_portfolio_comments_user_id", table_name="portfolio_comments")
    op.drop_index("ix_portfolio_comments_share_created", table_name="portfolio_comments")
    op.drop_table("portfolio_comments")
