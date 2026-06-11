"""ai_advice 테이블 — AI 투자 조언 영속화 (SPEC-STOCK-014)

Revision ID: 0015
Revises: 0014
Create Date: 2026-06-11

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import TIMESTAMP as TIMESTAMPTZ

# revision identifiers, used by Alembic.
revision: str = "0015"
down_revision: str | None = "0014"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "ai_advice",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("advice_type", sa.String(20), nullable=False),
        sa.Column("ref_date", sa.Date(), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("body", sa.Text(), nullable=True),
        sa.Column("payload", sa.Text(), nullable=True),
        sa.Column("risk_score", sa.Integer(), nullable=True),
        sa.Column("feedback", sa.String(20), nullable=True),
        sa.Column("feedback_at", TIMESTAMPTZ(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            TIMESTAMPTZ(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        # 동일 사용자·타입·기준일 조언 1회만 허용 (멱등성·캐싱 보장)
        sa.UniqueConstraint(
            "user_id", "advice_type", "ref_date",
            name="uq_ai_advice_user_type_date",
        ),
    )
    # 사용자별 타입별 최신 이력 조회 최적화 인덱스
    op.create_index(
        "ix_ai_advice_user_type",
        "ai_advice",
        ["user_id", "advice_type", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_ai_advice_user_type", table_name="ai_advice")
    op.drop_table("ai_advice")
