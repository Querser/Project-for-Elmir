"""stage4 ratings

Revision ID: 8f3c2a1d9b71
Revises: 7b2c9c0a1f14
Create Date: 2026-01-07
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "8f3c2a1d9b71"
down_revision: Union[str, Sequence[str], None] = "7b2c9c0a1f14"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "ratings",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("training_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("value", sa.SmallInteger(), nullable=False),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["training_id"], ["trainings.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("training_id", "user_id", name="uq_ratings_training_user"),
    )

    op.create_index("ix_ratings_id", "ratings", ["id"], unique=False)
    op.create_index("ix_ratings_training_id", "ratings", ["training_id"], unique=False)
    op.create_index("ix_ratings_user_id", "ratings", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_ratings_user_id", table_name="ratings")
    op.drop_index("ix_ratings_training_id", table_name="ratings")
    op.drop_index("ix_ratings_id", table_name="ratings")
    op.drop_table("ratings")
