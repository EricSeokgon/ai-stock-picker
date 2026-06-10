"""sector_trends (sector, trade_date) UNIQUE 제약조건 추가 (SPEC-STOCK-008 TASK-001)

Revision ID: 0011
Revises: 0010
Create Date: 2026-06-10
"""

from alembic import op

revision = "0011"
down_revision = "0010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """sector_trends 테이블에 (sector, trade_date) 유니크 제약조건 추가."""
    op.create_unique_constraint(
        "uq_sector_trends_sector_date",
        "sector_trends",
        ["sector", "trade_date"],
    )


def downgrade() -> None:
    """sector_trends 테이블에서 유니크 제약조건 제거."""
    op.drop_constraint(
        "uq_sector_trends_sector_date",
        "sector_trends",
        type_="unique",
    )
