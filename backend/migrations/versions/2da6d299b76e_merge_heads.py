"""merge heads

Revision ID: 2da6d299b76e
Revises: 20260127_levels_tz_sort_order, 9c4f7d2a31b8
Create Date: 2026-01-28 16:58:15.018467

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2da6d299b76e'
down_revision: Union[str, Sequence[str], None] = ('20260127_levels_tz_sort_order', '9c4f7d2a31b8')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
