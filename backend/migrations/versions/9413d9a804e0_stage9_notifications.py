"""stage9 notifications

Revision ID: 9413d9a804e0
Revises: 61e11b4460f0
Create Date: 2025-12-29 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa

revision = "9413d9a804e0"
down_revision = "61e11b4460f0"
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
    if _table_exists("notifications"):
        return

    op.create_table(
        "notifications",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column(
            "is_read",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index("ix_notifications_id", "notifications", ["id"], unique=False)
    op.create_index(
        "ix_notifications_user_id", "notifications", ["user_id"], unique=False
    )
    op.create_index("ix_notifications_is_read", "notifications", ["is_read"], unique=False)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS notifications CASCADE;")
