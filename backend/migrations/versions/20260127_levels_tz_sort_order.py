"""levels: привести к ТЗ + заполнить sort_order (fix NOT NULL)

Revision ID: 20260127_levels_tz_sort_order
Revises: REPLACE_WITH_DB_HEAD
Create Date: 2026-01-27
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect, text

# revision identifiers, used by Alembic.
revision = "20260127_levels_tz_sort_order"
down_revision = "7e1f74384b83"
branch_labels = None
depends_on = None

LEVELS = [
    ("Новичок", 10),
    ("Средний-", 20),
    ("Средний", 30),
    ("Средний+", 40),
]


def _table_exists(insp, name: str) -> bool:
    return name in insp.get_table_names()


def _col_exists(insp, table: str, col: str) -> bool:
    return any(c["name"] == col for c in insp.get_columns(table))


def upgrade() -> None:
    bind = op.get_bind()
    insp = inspect(bind)

    # Если вдруг таблицы нет (в редких случаях) — создаём минимально.
    # Обычно у тебя она есть, это просто safety.
    if not _table_exists(insp, "levels"):
        op.create_table(
            "levels",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("name", sa.String(length=255), nullable=False),
            sa.Column("sort_order", sa.Integer(), nullable=True),
        )
        insp = inspect(bind)

    # Если sort_order ещё не существует — добавляем nullable, потом заполним и сделаем NOT NULL.
    if not _col_exists(insp, "levels", "sort_order"):
        op.add_column("levels", sa.Column("sort_order", sa.Integer(), nullable=True))

    # 1) upsert 4 уровня по ТЗ без ON CONFLICT (чтобы не зависеть от уникальных индексов)
    for name, order in LEVELS:
        bind.execute(
            text("UPDATE levels SET sort_order = :order WHERE name = :name"),
            {"name": name, "order": order},
        )
        bind.execute(
            text(
                """
                INSERT INTO levels (name, sort_order)
                SELECT :name, :order
                WHERE NOT EXISTS (SELECT 1 FROM levels WHERE name = :name)
                """
            ),
            {"name": name, "order": order},
        )

    # 2) всем остальным (если есть) проставим sort_order, чтобы не было NULL
    bind.execute(
        text(
            """
            UPDATE levels
            SET sort_order = COALESCE(sort_order, id * 10)
            WHERE sort_order IS NULL
            """
        )
    )

    # 3) делаем NOT NULL (после заполнения)
    op.alter_column("levels", "sort_order", existing_type=sa.Integer(), nullable=False)


def downgrade() -> None:
    # Откат: делаем sort_order nullable (данные не трогаем)
    op.alter_column("levels", "sort_order", existing_type=sa.Integer(), nullable=True)
