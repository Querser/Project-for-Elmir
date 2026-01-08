"""stage11 settings + audit logs

Revision ID: 35006da0fcc7
Revises: 9413d9a804e0
Create Date: 2025-12-30 10:06:52.240988
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect, text
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "35006da0fcc7"
down_revision: Union[str, Sequence[str], None] = "9413d9a804e0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _table_exists(insp, table_name: str) -> bool:
    return table_name in insp.get_table_names()


def _col_exists(insp, table_name: str, col_name: str) -> bool:
    cols = {c["name"] for c in insp.get_columns(table_name)}
    return col_name in cols


def _index_exists(insp, table_name: str, index_name: str) -> bool:
    idx = {i["name"] for i in insp.get_indexes(table_name)}
    return index_name in idx


def upgrade() -> None:
    bind = op.get_bind()
    insp = inspect(bind)

    # ---------------------------------------------------------------------
    # 0) debts: в исходной цепочке миграций дальше есть "restore debts".
    #    Чтобы restore не упал на "table exists", удаляем debts здесь (если есть).
    # ---------------------------------------------------------------------
    if _table_exists(insp, "debts"):
        op.execute("DROP TABLE IF EXISTS debts CASCADE;")

    # ---------------------------------------------------------------------
    # 1) audit_logs: создаём таблицу если её нет, иначе аккуратно доапгрейдим
    # ---------------------------------------------------------------------
    insp = inspect(bind)
    if not _table_exists(insp, "audit_logs"):
        op.create_table(
            "audit_logs",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("user_id", sa.Integer(), nullable=True),
            sa.Column("action", sa.String(length=50), nullable=True),
            sa.Column("entity", sa.String(length=50), nullable=True),
            sa.Column("entity_id", sa.Integer(), nullable=True),
            sa.Column("data", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
            sa.Column("ip", sa.String(length=50), nullable=True),
            sa.Column("user_agent", sa.String(length=255), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        )
    else:
        # add missing columns
        if not _col_exists(insp, "audit_logs", "entity"):
            op.add_column("audit_logs", sa.Column("entity", sa.String(length=50), nullable=True))
        if not _col_exists(insp, "audit_logs", "entity_id"):
            op.add_column("audit_logs", sa.Column("entity_id", sa.Integer(), nullable=True))
        if not _col_exists(insp, "audit_logs", "data"):
            op.add_column("audit_logs", sa.Column("data", postgresql.JSONB(astext_type=sa.Text()), nullable=True))
        if not _col_exists(insp, "audit_logs", "ip"):
            op.add_column("audit_logs", sa.Column("ip", sa.String(length=50), nullable=True))
        if not _col_exists(insp, "audit_logs", "user_agent"):
            op.add_column("audit_logs", sa.Column("user_agent", sa.String(length=255), nullable=True))
        if not _col_exists(insp, "audit_logs", "updated_at"):
            op.add_column(
                "audit_logs",
                sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            )

        # drop legacy columns if exist
        insp = inspect(bind)
        if _col_exists(insp, "audit_logs", "object_type"):
            op.drop_column("audit_logs", "object_type")
        if _col_exists(insp, "audit_logs", "meta"):
            op.drop_column("audit_logs", "meta")
        if _col_exists(insp, "audit_logs", "object_id"):
            op.drop_column("audit_logs", "object_id")

    # indexes for audit_logs
    insp = inspect(bind)
    if _table_exists(insp, "audit_logs"):
        if not _index_exists(insp, "audit_logs", "ix_audit_logs_action") and _col_exists(insp, "audit_logs", "action"):
            op.create_index("ix_audit_logs_action", "audit_logs", ["action"], unique=False)
        if not _index_exists(insp, "audit_logs", "ix_audit_logs_entity") and _col_exists(insp, "audit_logs", "entity"):
            op.create_index("ix_audit_logs_entity", "audit_logs", ["entity"], unique=False)
        if not _index_exists(insp, "audit_logs", "ix_audit_logs_entity_id") and _col_exists(insp, "audit_logs", "entity_id"):
            op.create_index("ix_audit_logs_entity_id", "audit_logs", ["entity_id"], unique=False)
        if not _index_exists(insp, "audit_logs", "ix_audit_logs_user_id") and _col_exists(insp, "audit_logs", "user_id"):
            op.create_index("ix_audit_logs_user_id", "audit_logs", ["user_id"], unique=False)

    # ---------------------------------------------------------------------
    # 2) bans.reason -> NOT NULL + индекс по user_id
    # ---------------------------------------------------------------------
    insp = inspect(bind)
    if _table_exists(insp, "bans") and _col_exists(insp, "bans", "reason"):
        nulls = bind.execute(text("SELECT COUNT(*) FROM bans WHERE reason IS NULL")).scalar() or 0
        if nulls > 0:
            bind.execute(text("UPDATE bans SET reason = '' WHERE reason IS NULL"))

        op.alter_column("bans", "reason", existing_type=sa.VARCHAR(length=255), nullable=False)

        insp = inspect(bind)
        if _col_exists(insp, "bans", "user_id") and not _index_exists(insp, "bans", "ix_bans_user_id"):
            op.create_index("ix_bans_user_id", "bans", ["user_id"], unique=False)

    # ---------------------------------------------------------------------
    # 3) notifications: ГЛАВНЫЙ ФИКС — entity_id/ entity_type могут отсутствовать
    # ---------------------------------------------------------------------
    insp = inspect(bind)
    if _table_exists(insp, "notifications"):
        # гарантируем, что колонки существуют (иначе create_index падает)
        if not _col_exists(insp, "notifications", "entity_id"):
            op.add_column("notifications", sa.Column("entity_id", sa.Integer(), nullable=True))
        insp = inspect(bind)
        if not _col_exists(insp, "notifications", "entity_type"):
            op.add_column("notifications", sa.Column("entity_type", sa.String(length=50), nullable=True))

        # user_id NOT NULL — только если NULL'ов нет
        insp = inspect(bind)
        if _col_exists(insp, "notifications", "user_id"):
            nulls = bind.execute(text("SELECT COUNT(*) FROM notifications WHERE user_id IS NULL")).scalar() or 0
            if nulls == 0:
                op.alter_column("notifications", "user_id", existing_type=sa.INTEGER(), nullable=False)

        # индексы — только если есть соответствующая колонка
        insp = inspect(bind)
        if _col_exists(insp, "notifications", "entity_id") and not _index_exists(insp, "notifications", "ix_notifications_entity_id"):
            op.create_index("ix_notifications_entity_id", "notifications", ["entity_id"], unique=False)
        if _col_exists(insp, "notifications", "entity_type") and not _index_exists(insp, "notifications", "ix_notifications_entity_type"):
            op.create_index("ix_notifications_entity_type", "notifications", ["entity_type"], unique=False)
        if _col_exists(insp, "notifications", "type") and not _index_exists(insp, "notifications", "ix_notifications_type"):
            op.create_index("ix_notifications_type", "notifications", ["type"], unique=False)

    # ---------------------------------------------------------------------
    # 4) settings: создаём если нет; иначе доводим до нужной схемы
    # ---------------------------------------------------------------------
    insp = inspect(bind)
    op.execute("CREATE SEQUENCE IF NOT EXISTS settings_id_seq;")

    if not _table_exists(insp, "settings"):
        op.create_table(
            "settings",
            sa.Column("id", sa.Integer(), server_default=sa.text("nextval('settings_id_seq')"), primary_key=True),
            sa.Column("key", sa.String(length=150), nullable=False),
            sa.Column("value", sa.Text(), nullable=True),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.UniqueConstraint("key", name="uq_settings_key"),
        )
    else:
        # key length -> 150 (если есть)
        insp = inspect(bind)
        if _col_exists(insp, "settings", "key"):
            # через raw sql, чтобы не зависеть от existing_type
            op.execute("ALTER TABLE settings ALTER COLUMN key TYPE VARCHAR(150);")

        # description -> TEXT (если есть)
        insp = inspect(bind)
        if _col_exists(insp, "settings", "description"):
            op.execute("ALTER TABLE settings ALTER COLUMN description TYPE TEXT;")

        # created_at / updated_at
        insp = inspect(bind)
        if not _col_exists(insp, "settings", "created_at"):
            op.add_column("settings", sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False))
        if not _col_exists(insp, "settings", "updated_at"):
            op.add_column("settings", sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False))

        # id column (если нет — добавим сразу NOT NULL с DEFAULT)
        insp = inspect(bind)
        if not _col_exists(insp, "settings", "id"):
            op.add_column(
                "settings",
                sa.Column("id", sa.Integer(), server_default=sa.text("nextval('settings_id_seq')"), nullable=False),
            )
        else:
            op.execute("ALTER TABLE settings ALTER COLUMN id SET DEFAULT nextval('settings_id_seq');")
            op.execute("UPDATE settings SET id = nextval('settings_id_seq') WHERE id IS NULL;")

        # выравниваем sequence
        op.execute("SELECT setval('settings_id_seq', COALESCE((SELECT MAX(id) FROM settings), 0) + 1, false);")

        # ensure unique key (если нет constraint)
        # не пытаемся добавлять constraint через инспектор (сложно), просто создадим unique index если не существует
        insp = inspect(bind)
        if _col_exists(insp, "settings", "key") and not _index_exists(insp, "settings", "ix_settings_key"):
            op.create_index("ix_settings_key", "settings", ["key"], unique=True)

    # indexes for settings
    insp = inspect(bind)
    if _table_exists(insp, "settings"):
        if _col_exists(insp, "settings", "id") and not _index_exists(insp, "settings", "ix_settings_id"):
            op.create_index("ix_settings_id", "settings", ["id"], unique=False)
        if _col_exists(insp, "settings", "key") and not _index_exists(insp, "settings", "ix_settings_key"):
            op.create_index("ix_settings_key", "settings", ["key"], unique=True)


def downgrade() -> None:
    bind = op.get_bind()
    insp = inspect(bind)

    # settings
    if _table_exists(insp, "settings"):
        insp = inspect(bind)
        if _index_exists(insp, "settings", "ix_settings_key"):
            op.drop_index("ix_settings_key", table_name="settings")
        if _index_exists(insp, "settings", "ix_settings_id"):
            op.drop_index("ix_settings_id", table_name="settings")

        op.drop_table("settings")

    op.execute("DROP SEQUENCE IF EXISTS settings_id_seq;")

    # notifications indexes
    insp = inspect(bind)
    if _table_exists(insp, "notifications"):
        insp = inspect(bind)
        if _index_exists(insp, "notifications", "ix_notifications_type"):
            op.drop_index("ix_notifications_type", table_name="notifications")
        if _index_exists(insp, "notifications", "ix_notifications_entity_type"):
            op.drop_index("ix_notifications_entity_type", table_name="notifications")
        if _index_exists(insp, "notifications", "ix_notifications_entity_id"):
            op.drop_index("ix_notifications_entity_id", table_name="notifications")

    # bans.reason nullable back
    insp = inspect(bind)
    if _table_exists(insp, "bans") and _col_exists(insp, "bans", "reason"):
        insp = inspect(bind)
        if _index_exists(insp, "bans", "ix_bans_user_id"):
            op.drop_index("ix_bans_user_id", table_name="bans")
        op.alter_column("bans", "reason", existing_type=sa.VARCHAR(length=255), nullable=True)

    # audit_logs
    insp = inspect(bind)
    if _table_exists(insp, "audit_logs"):
        insp = inspect(bind)
        if _index_exists(insp, "audit_logs", "ix_audit_logs_user_id"):
            op.drop_index("ix_audit_logs_user_id", table_name="audit_logs")
        if _index_exists(insp, "audit_logs", "ix_audit_logs_entity_id"):
            op.drop_index("ix_audit_logs_entity_id", table_name="audit_logs")
        if _index_exists(insp, "audit_logs", "ix_audit_logs_entity"):
            op.drop_index("ix_audit_logs_entity", table_name="audit_logs")
        if _index_exists(insp, "audit_logs", "ix_audit_logs_action"):
            op.drop_index("ix_audit_logs_action", table_name="audit_logs")

        op.drop_table("audit_logs")

    # debts не восстанавливаем тут — это отдельно в restore_debts миграции
