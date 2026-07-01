"""포트폴리오 거래 원장 테이블 신규 (SPEC-STOCK-049)

Revision ID: 0030
Revises: 0029
Create Date: 2026-07-01
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = "0030"
down_revision = "0029"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 거래 원장 테이블: 개별 매수/매도 거래 기록
    op.create_table(
        "portfolio_transactions",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "portfolio_id",
            sa.Integer(),
            sa.ForeignKey("portfolios.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("krx_code", sa.String(20), nullable=False),
        sa.Column(
            "txn_type",
            sa.String(4),
            sa.CheckConstraint("txn_type IN ('BUY', 'SELL')", name="ck_portfolio_transactions_txn_type"),
            nullable=False,
        ),
        sa.Column(
            "quantity",
            sa.Integer(),
            sa.CheckConstraint("quantity > 0", name="ck_portfolio_transactions_quantity"),
            nullable=False,
        ),
        sa.Column(
            "price",
            sa.Numeric(18, 2),
            sa.CheckConstraint("price > 0", name="ck_portfolio_transactions_price"),
            nullable=False,
        ),
        sa.Column("txn_date", sa.Date(), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    # (portfolio_id, krx_code) 복합 인덱스 — 종목별 거래 조회 최적화
    op.create_index(
        "ix_portfolio_transactions_portfolio_id",
        "portfolio_transactions",
        ["portfolio_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_portfolio_transactions_portfolio_id", table_name="portfolio_transactions")
    op.drop_table("portfolio_transactions")
