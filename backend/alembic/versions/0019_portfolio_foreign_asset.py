"""portfolio_holdings — market/currency 컬럼 추가, 복합 UNIQUE 제약 추가 (SPEC-STOCK-028)

Revision ID: 0019
Revises: 0018
Create Date: 2026-06-22

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0019"
down_revision: str | None = "0018"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """portfolio_holdings에 market, currency 컬럼 추가 및 복합 UNIQUE 제약 생성."""
    # market: 상장 거래소 (KRX 기본값)
    op.add_column(
        "portfolio_holdings",
        sa.Column(
            "market",
            sa.String(10),
            nullable=False,
            server_default="KRX",
        ),
    )
    # currency: 결제 통화 (KRW 기본값)
    op.add_column(
        "portfolio_holdings",
        sa.Column(
            "currency",
            sa.String(3),
            nullable=False,
            server_default="KRW",
        ),
    )
    # (portfolio_id, krx_code, market) 복합 UNIQUE — 동일 시장 내 종목 중복 방지
    op.create_unique_constraint(
        "uq_holding_portfolio_ticker_market",
        "portfolio_holdings",
        ["portfolio_id", "krx_code", "market"],
    )


def downgrade() -> None:
    """추가된 제약 및 컬럼 제거."""
    op.drop_constraint(
        "uq_holding_portfolio_ticker_market",
        "portfolio_holdings",
        type_="unique",
    )
    op.drop_column("portfolio_holdings", "currency")
    op.drop_column("portfolio_holdings", "market")
