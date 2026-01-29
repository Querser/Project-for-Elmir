"""merge heads stage12 and ratings

Revision ID: 7e1f74384b83
Revises: 5c1d0aa9c4b2, f6b38fb4810f
Create Date: 2026-01-23 17:53:16.201498

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7e1f74384b83'
down_revision: Union[str, Sequence[str], None] = ('5c1d0aa9c4b2', 'f6b38fb4810f')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
