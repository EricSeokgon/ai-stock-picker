"""포트폴리오 공유 & 소셜 테이블 생성 (SPEC-STOCK-042)

Revision ID: 0026
Revises: 0025
Create Date: 2026-06-30

portfolio_shares: 포트폴리오 공유 링크 관리 테이블.
  - share_token: 고유 랜덤 토큰 (secrets.token_urlsafe(16), 22자, VARCHAR(32))
  - share_url: 상대 경로 공유 URL (/shared/{token})
  - is_public: 공개 여부 (DELETE 시 False, 소프트 삭제)
  - view_count: 조회수 (원자적 증가, UPDATE SET view_count = view_count + 1)

portfolio_likes: 포트폴리오 좋아요 테이블.
  - (share_id, user_id) 복합 유니크 — 중복 좋아요 DB 레벨 방지
  - like_count는 COUNT(*) 쿼리로 파생 (비정규화 카운터 없음)
  - 소유자 좋아요 금지는 앱 레벨에서 강제 (403)
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = "0026"
down_revision = "0025"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # portfolio_shares 테이블
    op.create_table(
        "portfolio_shares",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("portfolio_id", sa.Integer(), nullable=False),
        # share_token: secrets.token_urlsafe(16) 생성, 22자, VARCHAR(32)
        sa.Column("share_token", sa.String(32), nullable=False),
        # share_url: 상대 경로 (/shared/{token})
        sa.Column("share_url", sa.String(128), nullable=False),
        # is_public: 공개 여부 (소프트 삭제 시 False)
        sa.Column("is_public", sa.Boolean(), nullable=False, server_default="true"),
        # view_count: 조회수 (원자적 UPDATE, 기본 0)
        sa.Column("view_count", sa.Integer(), nullable=False, server_default="0"),
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
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["portfolio_id"],
            ["portfolios.id"],
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint("share_token", name="uq_portfolio_shares_token"),
        sa.UniqueConstraint("portfolio_id", name="uq_portfolio_shares_portfolio_id"),
    )
    op.create_index(
        "ix_portfolio_shares_portfolio_id",
        "portfolio_shares",
        ["portfolio_id"],
    )
    op.create_index(
        "ix_portfolio_shares_is_public",
        "portfolio_shares",
        ["is_public"],
    )

    # portfolio_likes 테이블
    op.create_table(
        "portfolio_likes",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("share_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["share_id"],
            ["portfolio_shares.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            ondelete="CASCADE",
        ),
        # (share_id, user_id) 복합 유니크 — 중복 좋아요 DB 레벨 방지
        sa.UniqueConstraint("share_id", "user_id", name="uq_portfolio_likes_share_user"),
    )
    op.create_index(
        "ix_portfolio_likes_share_id",
        "portfolio_likes",
        ["share_id"],
    )
    op.create_index(
        "ix_portfolio_likes_user_id",
        "portfolio_likes",
        ["user_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_portfolio_likes_user_id", table_name="portfolio_likes")
    op.drop_index("ix_portfolio_likes_share_id", table_name="portfolio_likes")
    op.drop_table("portfolio_likes")

    op.drop_index("ix_portfolio_shares_is_public", table_name="portfolio_shares")
    op.drop_index("ix_portfolio_shares_portfolio_id", table_name="portfolio_shares")
    op.drop_table("portfolio_shares")
