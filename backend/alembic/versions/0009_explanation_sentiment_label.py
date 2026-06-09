"""recommendations.explanation 및 analysis_results.sentiment_label 컬럼 추가

Revision ID: 0009
Revises: 0008
Create Date: 2026-06-10
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# 리비전 식별자
revision: str = "0009"
down_revision: Union[str, None] = "0008"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """recommendations.explanation, analysis_results.sentiment_label 컬럼 추가"""
    # 추천 근거 텍스트 (Claude가 생성한 한국어 2~3문장)
    op.add_column(
        "recommendations",
        sa.Column("explanation", sa.Text(), nullable=True),
    )
    # 감성 점수의 5단계 라벨 (매우긍정/긍정/중립/부정/매우부정)
    op.add_column(
        "analysis_results",
        sa.Column("sentiment_label", sa.String(length=20), nullable=True),
    )


def downgrade() -> None:
    """추가한 컬럼 롤백"""
    op.drop_column("analysis_results", "sentiment_label")
    op.drop_column("recommendations", "explanation")
