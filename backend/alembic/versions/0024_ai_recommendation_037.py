"""AI 개인화 추천 테이블 생성 (SPEC-STOCK-037)

Revision ID: 0024
Revises: 0023
Create Date: 2026-06-25

recommendation_preferences: 사용자별 종목 선호(좋아요/싫어요) 저장 테이블.
recommendation_history: AI 개인화 추천 히스토리 스냅샷 저장 테이블.
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "0024"
down_revision = "0023"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # recommendation_preferences: 사용자별 종목 선호 테이블 (REQ-AIEX-PREF)
    op.create_table(
        "recommendation_preferences",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("portfolio_id", sa.Integer(), nullable=False),
        sa.Column("krx_code", sa.String(length=10), nullable=False),
        sa.Column("sector", sa.String(length=50), nullable=True),
        # "liked" 또는 "disliked" 값만 허용 (REQ-AIEX-APPLY)
        sa.Column("preference", sa.String(length=8), nullable=False),
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
            ["user_id"], ["users.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["portfolio_id"], ["portfolios.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        # (user_id, portfolio_id, krx_code) 복합 UNIQUE — 중복 선호 방지
        sa.UniqueConstraint(
            "user_id", "portfolio_id", "krx_code",
            name="uq_rec_preference_user_pf_code",
        ),
    )

    # recommendation_history: AI 추천 히스토리 스냅샷 테이블 (REQ-AIEX-HIST)
    op.create_table(
        "recommendation_history",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("portfolio_id", sa.Integer(), nullable=False),
        # 추천 항목 목록 JSON 직렬화 (SQLite 호환 Text)
        sa.Column("recommendations", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["portfolio_id"], ["portfolios.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    # (user_id, portfolio_id, created_at) 최신순 조회 최적화 인덱스
    op.create_index(
        "ix_rec_history_user_pf_created",
        "recommendation_history",
        ["user_id", "portfolio_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_rec_history_user_pf_created", table_name="recommendation_history")
    op.drop_table("recommendation_history")
    op.drop_table("recommendation_preferences")
