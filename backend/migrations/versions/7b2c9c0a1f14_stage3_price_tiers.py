"""stage3 price tiers

Revision ID: 7b2c9c0a1f14
Revises: 188cb79f8ead
Create Date: 2026-01-07 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa

revision = "7b2c9c0a1f14"
down_revision = "188cb79f8ead"
branch_labels = None
depends_on = None


def _table_exists(name: str) -> bool:
    bind = op.get_bind()
    res = bind.execute(
        sa.text("SELECT to_regclass(:t)"),
        {"t": f"public.{name}"},
    ).scalar()
    return res is not None


def upgrade() -> None:
    if _table_exists("price_tiers"):
        return

    op.create_table(
        "price_tiers",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("training_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("price", sa.Numeric(10, 2), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default=sa.text("1")),
        sa.Column("level_id", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["training_id"], ["trainings.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["level_id"], ["levels.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index("ix_price_tiers_id", "price_tiers", ["id"], unique=False)
    op.create_index("ix_price_tiers_training_id", "price_tiers", ["training_id"], unique=False)
    op.create_index("ix_price_tiers_level_id", "price_tiers", ["level_id"], unique=False)
    op.create_index("ix_price_tiers_sort_order", "price_tiers", ["sort_order"], unique=False)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS price_tiers CASCADE;")
