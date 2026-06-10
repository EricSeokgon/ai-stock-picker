"""추천 피드백 테이블 추가 (SPEC-STOCK-007 TASK-001)

Revision ID: 0010
Revises: 0009
Create Date: 2026-06-10
"""

from alembic import op
import sqlalchemy as sa

revision = "0010"
down_revision = "0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """recommendation_feedback 테이블 생성."""
    op.create_table(
        "recommendation_feedback",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("krx_code", sa.String(10), nullable=False),
        sa.Column("vote", sa.String(4), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_recommendation_feedback_krx_code",
        "recommendation_feedback",
        ["krx_code"],
    )


def downgrade() -> None:
    """recommendation_feedback 테이블 삭제."""
    op.drop_index("ix_recommendation_feedback_krx_code", table_name="recommendation_feedback")
    op.drop_table("recommendation_feedback")
