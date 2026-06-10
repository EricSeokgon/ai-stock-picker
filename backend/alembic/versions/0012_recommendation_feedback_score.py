"""recommendations 테이블에 base_score, feedback_score 컬럼 추가 (SPEC-STOCK-009 TASK-001)

Revision ID: 0012
Revises: 0011
Create Date: 2026-06-10
"""

import sqlalchemy as sa
from alembic import op

revision = "0012"
down_revision = "0011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """recommendations 테이블에 base_score, feedback_score 컬럼 추가."""
    op.add_column(
        "recommendations",
        sa.Column("base_score", sa.Numeric(6, 3), nullable=True),
    )
    op.add_column(
        "recommendations",
        sa.Column("feedback_score", sa.Numeric(6, 3), nullable=True),
    )


def downgrade() -> None:
    """recommendations 테이블에서 base_score, feedback_score 컬럼 제거."""
    op.drop_column("recommendations", "feedback_score")
    op.drop_column("recommendations", "base_score")
