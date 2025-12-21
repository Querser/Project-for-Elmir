"""stage8 debts

Revision ID: 8449a8479e9c
Revises: 34b9757e9dc2
Create Date: 2025-12-21
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "8449a8479e9c"
down_revision = "34b9757e9dc2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1) Создаём тип безопасно (если его нет) через SQL
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1
                FROM pg_type t
                JOIN pg_namespace n ON n.oid = t.typnamespace
                WHERE t.typname = 'debtstatus' AND n.nspname = 'public'
            ) THEN
                CREATE TYPE public.debtstatus AS ENUM ('OPEN', 'CLOSED');
            END IF;
        END $$;
        """
    )

    # 2) ВАЖНО: create_type=False отключает автосоздание типа при create_table
    debtstatus = postgresql.ENUM(
        "OPEN",
        "CLOSED",
        name="debtstatus",
        schema="public",
        create_type=False,
    )

    op.create_table(
        "debts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("training_id", sa.Integer(), sa.ForeignKey("trainings.id", ondelete="CASCADE"), nullable=False),
        sa.Column("amount", sa.Numeric(10, 2), nullable=False, server_default=sa.text("0")),
        sa.Column(
            "status",
            debtstatus,
            nullable=False,
            server_default=sa.text("'OPEN'::public.debtstatus"),
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("user_id", "training_id", name="uq_debt_user_training"),
    )

    op.create_index("ix_debts_user_id", "debts", ["user_id"])
    op.create_index("ix_debts_training_id", "debts", ["training_id"])
    op.create_index("ix_debts_status", "debts", ["status"])


def downgrade() -> None:
    op.drop_index("ix_debts_status", table_name="debts")
    op.drop_index("ix_debts_training_id", table_name="debts")
    op.drop_index("ix_debts_user_id", table_name="debts")
    op.drop_table("debts")

    op.execute("DROP TYPE IF EXISTS public.debtstatus;")
