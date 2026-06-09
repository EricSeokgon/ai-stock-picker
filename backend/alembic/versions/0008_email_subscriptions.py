"""email_subscriptions 테이블 추가 마이그레이션

Revision ID: 0008
Revises: 0007
Create Date: 2026-06-09
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# 리비전 식별자
revision: str = "0008"
down_revision: Union[str, None] = "0007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """email_subscriptions 테이블 생성"""
    op.create_table(
        "email_subscriptions",
        sa.Column("id", sa.Integer(), nullable=False, autoincrement=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            ondelete="CASCADE",
            name="fk_email_subscriptions_user_id",
        ),
        # 사용자당 이메일 구독 1개 제한
        sa.UniqueConstraint("user_id", name="uq_email_sub_user"),
    )
    op.create_index(
        "ix_email_subscriptions_user_id", "email_subscriptions", ["user_id"]
    )


def downgrade() -> None:
    """email_subscriptions 테이블 롤백"""
    op.drop_index("ix_email_subscriptions_user_id", table_name="email_subscriptions")
    op.drop_table("email_subscriptions")
