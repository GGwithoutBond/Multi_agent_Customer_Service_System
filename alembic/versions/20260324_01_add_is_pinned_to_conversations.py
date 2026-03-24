"""add is_pinned to conversations

Revision ID: 20260324_01
Revises:
Create Date: 2026-03-24 18:30:00
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260324_01"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "conversations",
        sa.Column("is_pinned", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.create_index(
        "ix_conversations_is_pinned",
        "conversations",
        ["is_pinned"],
        unique=False,
    )
    op.alter_column("conversations", "is_pinned", server_default=None)


def downgrade() -> None:
    op.drop_index("ix_conversations_is_pinned", table_name="conversations")
    op.drop_column("conversations", "is_pinned")
