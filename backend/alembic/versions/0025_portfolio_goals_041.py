"""포트폴리오 목표 관리 테이블 생성 (SPEC-STOCK-041)

Revision ID: 0025
Revises: 0024
Create Date: 2026-06-29

portfolio_goals: 사용자가 포트폴리오에 투자 목표(목표 평가액, 목표 수익률, 달성 기한)를 설정하고
달성률을 추적하는 테이블.
포트폴리오당 활성 목표 1개 제한 (is_active=True 기준, 앱 레벨에서 강제).
소프트 삭제: is_active=False.
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "0025"
down_revision = "0024"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "portfolio_goals",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("portfolio_id", sa.Integer(), nullable=False),
        # target_amount: 목표 평가액 (KRW), Decimal(15,2)
        sa.Column("target_amount", sa.Numeric(precision=15, scale=2), nullable=True),
        # target_return_rate: 목표 수익률 (%), Decimal(8,4)
        sa.Column("target_return_rate", sa.Numeric(precision=8, scale=4), nullable=True),
        # deadline: 목표 달성 기한
        sa.Column("deadline", sa.Date(), nullable=True),
        # is_active: 활성 목표 여부 (소프트 삭제 시 False)
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        # goal_reached_notified: 목표 달성 알림 발송 여부 (멱등성 보장)
        sa.Column("goal_reached_notified", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["portfolio_id"], ["portfolios.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    # portfolio_id 기준 빠른 조회를 위한 인덱스
    op.create_index(
        "ix_portfolio_goals_portfolio_id",
        "portfolio_goals",
        ["portfolio_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_portfolio_goals_portfolio_id", table_name="portfolio_goals")
    op.drop_table("portfolio_goals")
