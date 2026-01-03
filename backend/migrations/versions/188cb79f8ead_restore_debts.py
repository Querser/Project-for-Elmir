"""restore debts

Revision ID: 188cb79f8ead
Revises: 35006da0fcc7
Create Date: 2025-12-30
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "188cb79f8ead"
down_revision = "35006da0fcc7"
branch_labels = None
depends_on = None


def _table_exists(name: str) -> bool:
    bind = op.get_bind()
    # Postgres way: to_regclass вернёт NULL если таблицы нет
    res = bind.execute(sa.text("SELECT to_regclass(:t)"), {"t": f"public.{name}"}).scalar()
    return res is not None


def upgrade() -> None:
    # ENUM может существовать (у тебя так и было)
    debtstatus_enum = postgresql.ENUM("OPEN", "CLOSED", name="debtstatus")
    debtstatus_enum.create(op.get_bind(), checkfirst=True)

    # Если debts уже есть — ничего не делаем
    if _table_exists("debts"):
        return

    debtstatus_existing = postgresql.ENUM(
        "OPEN", "CLOSED", name="debtstatus", create_type=False
    )

    op.create_table(
        "debts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("training_id", sa.Integer(), nullable=False),
        sa.Column("amount", sa.Numeric(10, 2), nullable=False),
        sa.Column(
            "status",
            debtstatus_existing,
            nullable=False,
            server_default=sa.text("'OPEN'"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["training_id"], ["trainings.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index("ix_debts_id", "debts", ["id"], unique=False)
    op.create_index("ix_debts_user_id", "debts", ["user_id"], unique=False)
    op.create_index("ix_debts_training_id", "debts", ["training_id"], unique=False)
    op.create_index("ix_debts_status", "debts", ["status"], unique=False)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS debts CASCADE;")
    # debtstatus НЕ дропаем
