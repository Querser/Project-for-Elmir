"""stage9 notifications

Revision ID: 9413d9a804e0
Revises: 61e11b4460f0
Create Date: 2025-12-23
"""

from alembic import op
import sqlalchemy as sa


revision = "9413d9a804e0"
down_revision = "61e11b4460f0"
branch_labels = None
depends_on = None


def _table_exists(bind, table_name: str) -> bool:
    insp = sa.inspect(bind)
    return table_name in insp.get_table_names()


def _get_columns(bind, table_name: str) -> dict[str, dict]:
    insp = sa.inspect(bind)
    return {c["name"]: c for c in insp.get_columns(table_name)}


def _get_indexes(bind, table_name: str) -> set[str]:
    insp = sa.inspect(bind)
    return {i["name"] for i in insp.get_indexes(table_name)}


def upgrade() -> None:
    bind = op.get_bind()

    # 1) создать таблицу, если её ещё нет
    if not _table_exists(bind, "notifications"):
        op.create_table(
            "notifications",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
            sa.Column("type", sa.String(length=50), nullable=False),
            sa.Column("text", sa.Text(), nullable=False),
            sa.Column("entity_type", sa.String(length=50), nullable=True),
            sa.Column("entity_id", sa.Integer(), nullable=True),
            sa.Column("url", sa.String(length=500), nullable=True),
            sa.Column("is_read", sa.Boolean(), nullable=False, server_default=sa.text("false")),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        )

    # 2) если таблица была раньше — аккуратно довести до нужных колонок/индексов
    cols = _get_columns(bind, "notifications")

    # type
    if "type" not in cols:
        op.add_column("notifications", sa.Column("type", sa.String(length=50), nullable=True))
        cols = _get_columns(bind, "notifications")
        if "kind" in cols:
            op.execute("UPDATE notifications SET type = kind WHERE type IS NULL")
        op.execute("UPDATE notifications SET type = 'SYSTEM' WHERE type IS NULL")
        op.alter_column("notifications", "type", nullable=False)

    # text
    cols = _get_columns(bind, "notifications")
    if "text" not in cols:
        op.add_column("notifications", sa.Column("text", sa.Text(), nullable=True))
        cols = _get_columns(bind, "notifications")
        if "body" in cols:
            op.execute("UPDATE notifications SET text = body WHERE text IS NULL")
        elif "message" in cols:
            op.execute("UPDATE notifications SET text = message WHERE text IS NULL")
        op.execute("UPDATE notifications SET text = '' WHERE text IS NULL")
        op.alter_column("notifications", "text", nullable=False)
    else:
        # если колонка есть — гарантируем, что там нет NULL
        op.execute("UPDATE notifications SET text = '' WHERE text IS NULL")
        op.execute("ALTER TABLE notifications ALTER COLUMN text SET NOT NULL")

    # entity_type / entity_id
    cols = _get_columns(bind, "notifications")
    if "entity_type" not in cols:
        op.add_column("notifications", sa.Column("entity_type", sa.String(length=50), nullable=True))
    if "entity_id" not in cols:
        op.add_column("notifications", sa.Column("entity_id", sa.Integer(), nullable=True))

    # url
    cols = _get_columns(bind, "notifications")
    if "url" not in cols:
        op.add_column("notifications", sa.Column("url", sa.String(length=500), nullable=True))
        cols = _get_columns(bind, "notifications")
        if "link" in cols:
            op.execute("UPDATE notifications SET url = link WHERE url IS NULL")

    # is_read (ВАЖНО: чиним DEFAULT и backfill даже если колонка уже существует)
    cols = _get_columns(bind, "notifications")
    if "is_read" not in cols:
        op.add_column(
            "notifications",
            sa.Column("is_read", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        )
    else:
        op.execute("ALTER TABLE notifications ALTER COLUMN is_read SET DEFAULT false")
        op.execute("UPDATE notifications SET is_read = false WHERE is_read IS NULL")
        op.execute("ALTER TABLE notifications ALTER COLUMN is_read SET NOT NULL")

    # created_at (тоже можно восстановить дефолт, если потерялся)
    cols = _get_columns(bind, "notifications")
    if "created_at" not in cols:
        op.add_column(
            "notifications",
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        )
    else:
        op.execute("ALTER TABLE notifications ALTER COLUMN created_at SET DEFAULT now()")
        op.execute("UPDATE notifications SET created_at = now() WHERE created_at IS NULL")
        op.execute("ALTER TABLE notifications ALTER COLUMN created_at SET NOT NULL")

    # индексы
    idx = _get_indexes(bind, "notifications")
    if "ix_notifications_user_id" not in idx:
        op.create_index("ix_notifications_user_id", "notifications", ["user_id"])
    if "ix_notifications_user_id_is_read" not in idx:
        op.create_index("ix_notifications_user_id_is_read", "notifications", ["user_id", "is_read"])
    if "ix_notifications_created_at" not in idx:
        op.create_index("ix_notifications_created_at", "notifications", ["created_at"])


def downgrade() -> None:
    # Безопасный downgrade: не дропаем таблицу (чтобы не снести данные).
    bind = op.get_bind()
    if not _table_exists(bind, "notifications"):
        return

    idx = _get_indexes(bind, "notifications")
    if "ix_notifications_user_id_is_read" in idx:
        op.drop_index("ix_notifications_user_id_is_read", table_name="notifications")
    if "ix_notifications_user_id" in idx:
        op.drop_index("ix_notifications_user_id", table_name="notifications")
    if "ix_notifications_created_at" in idx:
        op.drop_index("ix_notifications_created_at", table_name="notifications")
