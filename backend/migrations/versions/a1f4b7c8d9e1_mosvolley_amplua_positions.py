"""MosVolley amplua positions and enrollment position key

Revision ID: a1f4b7c8d9e1
Revises: c3b1a2f8d9e0
Create Date: 2026-03-18 00:00:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "a1f4b7c8d9e1"
down_revision = "c3b1a2f8d9e0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("trainings", sa.Column("training_type", sa.String(length=32), nullable=True))
    op.add_column("trainings", sa.Column("amplua_positions", sa.JSON(), nullable=True))
    op.add_column("enrollments", sa.Column("position_key", sa.String(length=50), nullable=True))


def downgrade() -> None:
    op.drop_column("enrollments", "position_key")
    op.drop_column("trainings", "amplua_positions")
    op.drop_column("trainings", "training_type")
