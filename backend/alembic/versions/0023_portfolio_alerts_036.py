"""portfolio_alerts 테이블에 SPEC-036 컬럼 추가 — target_krx_code, condition_direction

Revision ID: 0023
Revises: 0022
Create Date: 2026-06-25

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0023"
down_revision: str | None = "0022"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """portfolio_alerts 테이블에 SPEC-036 신규 컬럼 추가."""
    # target_krx_code: 종목 알림 대상 종목코드, NULL=비종목형 알림
    op.add_column(
        "portfolio_alerts",
        sa.Column("target_krx_code", sa.String(), nullable=True),
    )
    # condition_direction: 방향 조건 "above"/"below", NULL=above 기본값
    op.add_column(
        "portfolio_alerts",
        sa.Column("condition_direction", sa.String(5), nullable=True),
    )


def downgrade() -> None:
    """SPEC-036 컬럼 롤백."""
    op.drop_column("portfolio_alerts", "condition_direction")
    op.drop_column("portfolio_alerts", "target_krx_code")
