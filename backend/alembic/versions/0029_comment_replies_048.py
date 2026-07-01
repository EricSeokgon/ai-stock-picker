"""대댓글 지원: portfolio_comments.parent_comment_id 추가 (SPEC-STOCK-048)

Revision ID: 0029
Revises: 0028
Create Date: 2026-07-01
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = "0029"
down_revision = "0028"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # parent_comment_id: nullable self-FK (최상위 댓글은 NULL)
    op.add_column(
        "portfolio_comments",
        sa.Column("parent_comment_id", sa.Integer(), nullable=True),
    )
    # 자기참조 외래 키 (parent 삭제 시 replies cascade)
    op.create_foreign_key(
        "fk_portfolio_comments_parent",
        "portfolio_comments",
        "portfolio_comments",
        ["parent_comment_id"],
        ["id"],
        ondelete="CASCADE",
    )
    # 대댓글 배치 조회 최적화 인덱스 (REQ-REPLY-011)
    op.create_index(
        "ix_portfolio_comments_parent_id",
        "portfolio_comments",
        ["parent_comment_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_portfolio_comments_parent_id", table_name="portfolio_comments")
    op.drop_constraint(
        "fk_portfolio_comments_parent",
        "portfolio_comments",
        type_="foreignkey",
    )
    op.drop_column("portfolio_comments", "parent_comment_id")
