"""stage14 telegram avatar and integrations

Revision ID: c3b1a2f8d9e0
Revises: f91c5163dae0
Create Date: 2026-02-11
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "c3b1a2f8d9e0"
down_revision = "f91c5163dae0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("avatar_url", sa.String(length=500), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "avatar_url")

