"""초기 테이블 생성 마이그레이션

Revision ID: 0001
Revises:
Create Date: 2026-06-01
"""
from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import ARRAY
from alembic import op

# 리비전 식별자
revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """5개 테이블 초기 생성"""

    # articles 테이블: 뉴스 기사 수집
    op.create_table(
        "articles",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("url", sa.String(length=2048), nullable=False),
        sa.Column("source", sa.String(length=100), nullable=False),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("content", sa.Text(), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "collected_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="collected"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("url", name="uq_articles_url"),
    )

    # analysis_results 테이블: Claude API 분석 결과
    op.create_table(
        "analysis_results",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("article_id", sa.Integer(), nullable=False),
        sa.Column("sentiment", sa.String(length=20), nullable=False),
        sa.Column("sentiment_score", sa.Numeric(precision=4, scale=3), nullable=False),
        sa.Column("sector_tags", ARRAY(sa.String()), nullable=False),
        sa.Column("keywords", ARRAY(sa.String()), nullable=False),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("tokens_used", sa.Integer(), nullable=True),
        sa.Column(
            "analyzed_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["article_id"],
            ["articles.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    # stock_mentions 테이블: 기사 내 종목 언급
    op.create_table(
        "stock_mentions",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("article_id", sa.Integer(), nullable=False),
        sa.Column("stock_name", sa.String(length=100), nullable=False),
        sa.Column("krx_code", sa.String(length=10), nullable=True),
        sa.Column("mention_status", sa.String(length=50), nullable=False),
        sa.ForeignKeyConstraint(
            ["article_id"],
            ["articles.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    # sector_trends 테이블: 섹터별 일일 트렌드
    op.create_table(
        "sector_trends",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("sector", sa.String(length=100), nullable=False),
        sa.Column("trade_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("news_volume", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "avg_sentiment",
            sa.Numeric(precision=4, scale=3),
            nullable=False,
            server_default="0",
        ),
        sa.Column(
            "trend_score",
            sa.Numeric(precision=6, scale=3),
            nullable=False,
            server_default="0",
        ),
        sa.Column(
            "computed_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    # recommendations 테이블: 일일 종목/ETF 추천 결과
    op.create_table(
        "recommendations",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("trade_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("asset_type", sa.String(length=20), nullable=False),
        sa.Column("krx_code", sa.String(length=10), nullable=False),
        sa.Column("rank", sa.Integer(), nullable=False),
        sa.Column("total_score", sa.Numeric(precision=6, scale=3), nullable=False),
        sa.Column("sentiment_score", sa.Numeric(precision=6, scale=3), nullable=False, server_default="0"),
        sa.Column("volume_score", sa.Numeric(precision=6, scale=3), nullable=False, server_default="0"),
        sa.Column("momentum_score", sa.Numeric(precision=6, scale=3), nullable=False, server_default="0"),
        sa.Column("anomaly_score", sa.Numeric(precision=6, scale=3), nullable=False, server_default="0"),
        sa.Column("reasoning", sa.Text(), nullable=True),
        sa.Column(
            "computed_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    # 복합 인덱스: 날짜별, 자산유형별, 순위별 조회 최적화
    op.create_index(
        "ix_recommendations_date_type_rank",
        "recommendations",
        ["trade_date", "asset_type", "rank"],
    )


def downgrade() -> None:
    """테이블 롤백 - 역순으로 삭제"""
    op.drop_index("ix_recommendations_date_type_rank", table_name="recommendations")
    op.drop_table("recommendations")
    op.drop_table("sector_trends")
    op.drop_table("stock_mentions")
    op.drop_table("analysis_results")
    op.drop_table("articles")
