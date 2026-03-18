"""Training image gallery support

Revision ID: d2c7f9a1b4e6
Revises: a1f4b7c8d9e1
Create Date: 2026-03-18 00:00:01.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "d2c7f9a1b4e6"
down_revision = "a1f4b7c8d9e1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("trainings", sa.Column("image_urls", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("trainings", "image_urls")
