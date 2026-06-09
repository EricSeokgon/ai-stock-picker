"""telegram_subscriptions 테이블 추가 마이그레이션

Revision ID: 0003
Revises: 0002
Create Date: 2026-06-09
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# 리비전 식별자
revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """telegram_subscriptions 테이블 생성"""
    op.create_table(
        "telegram_subscriptions",
        sa.Column("id", sa.Integer(), nullable=False, autoincrement=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("chat_id", sa.BigInteger(), nullable=False),
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
        sa.Column(
            "subscribed_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("chat_id", name="uq_telegram_subs_chat_id"),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], ondelete="CASCADE", name="fk_telegram_subs_user_id"
        ),
    )
    op.create_index("ix_telegram_subs_user_id", "telegram_subscriptions", ["user_id"])
    op.create_index("ix_telegram_subs_chat_id", "telegram_subscriptions", ["chat_id"])


def downgrade() -> None:
    """telegram_subscriptions 테이블 롤백"""
    op.drop_index("ix_telegram_subs_chat_id", table_name="telegram_subscriptions")
    op.drop_index("ix_telegram_subs_user_id", table_name="telegram_subscriptions")
    op.drop_table("telegram_subscriptions")
