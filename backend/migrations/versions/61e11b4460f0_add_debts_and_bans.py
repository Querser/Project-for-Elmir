"""merge heads (stage8 debts/bans)

Revision ID: 61e11b4460f0
Revises: 8449a8479e9c
Create Date: 2025-12-18 19:09:18.930186

ВАЖНО:
- Эта ревизия раньше была авто-сгенерена и ломала схему (дропала active/until, меняла enum).
- В проекте уже есть корректные миграции stage8, поэтому здесь делаем NO-OP,
  чтобы:
  1) убрать "multiple heads"
  2) не портить схему, под которую уже написан код (ban_service, debt_service)
"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "61e11b4460f0"
down_revision: Union[str, Sequence[str], None] = "8449a8479e9c"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # NO-OP (merge)
    pass


def downgrade() -> None:
    # NO-OP (merge)
    pass
