"""stage12 enrollmentstatus reserve and cancelled late

Revision ID: 5c1d0aa9c4b2
Revises: 35006da0fcc7
Create Date: 2026-01-22
"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "5c1d0aa9c4b2"
down_revision = "35006da0fcc7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    Postgres ENUM ALTER TYPE не всегда можно выполнять внутри транзакции.
    Поэтому делаем через autocommit_block + проверку на существование значения.
    Добавляем оба значения, раз миграция stage12 это подразумевает.
    """
    ctx = op.get_context()
    with ctx.autocommit_block():
        op.execute(
            """
            DO $$
            BEGIN
                IF NOT EXISTS (
                    SELECT 1
                    FROM pg_enum e
                    JOIN pg_type t ON t.oid = e.enumtypid
                    WHERE t.typname = 'enrollmentstatus'
                      AND e.enumlabel = 'RESERVE'
                ) THEN
                    ALTER TYPE enrollmentstatus ADD VALUE 'RESERVE';
                END IF;

                IF NOT EXISTS (
                    SELECT 1
                    FROM pg_enum e
                    JOIN pg_type t ON t.oid = e.enumtypid
                    WHERE t.typname = 'enrollmentstatus'
                      AND e.enumlabel = 'CANCELLED_LATE'
                ) THEN
                    ALTER TYPE enrollmentstatus ADD VALUE 'CANCELLED_LATE';
                END IF;
            END $$;
            """
        )


def downgrade() -> None:
    # В Postgres нельзя просто удалить value из enum.
    pass
