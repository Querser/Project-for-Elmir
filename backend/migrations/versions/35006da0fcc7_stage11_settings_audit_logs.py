"""stage11 settings + audit logs

Revision ID: 35006da0fcc7
Revises: 9413d9a804e0
Create Date: 2025-12-30 10:06:52.240988
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from sqlalchemy import inspect, text

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
    # 0) (ОСТОРОЖНО) debts — в оригинале autogenerate почему-то удалял debts.
    #    Чтобы НЕ ЛОМАТЬ текущую цепочку миграций (у тебя есть restore_debts),
    #    оставляем поведение "удалить debts", но делаем это безопасно:
    #    только если таблица реально существует.
    # ---------------------------------------------------------------------
    if _table_exists(insp, "debts"):
        # индексы дропаем через IF EXISTS, чтобы не зависеть от naming convention
        op.execute("DROP INDEX IF EXISTS ix_debts_status;")
        op.execute("DROP INDEX IF EXISTS ix_debts_training_id;")
        op.execute("DROP INDEX IF EXISTS ix_debts_user_id;")
        op.execute("DROP INDEX IF EXISTS ix_debts_id;")
        op.execute("DROP TABLE IF EXISTS debts CASCADE;")

    # ---------------------------------------------------------------------
    # 1) audit_logs — добавляем новые поля/индексы максимально безопасно
    # ---------------------------------------------------------------------
    if _table_exists(insp, "audit_logs"):
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

        # индексы (создаём только если нет)
        insp = inspect(bind)
        if not _index_exists(insp, "audit_logs", "ix_audit_logs_action"):
            op.create_index("ix_audit_logs_action", "audit_logs", ["action"], unique=False)
        if not _index_exists(insp, "audit_logs", "ix_audit_logs_entity"):
            op.create_index("ix_audit_logs_entity", "audit_logs", ["entity"], unique=False)
        if not _index_exists(insp, "audit_logs", "ix_audit_logs_entity_id"):
            op.create_index("ix_audit_logs_entity_id", "audit_logs", ["entity_id"], unique=False)
        if not _index_exists(insp, "audit_logs", "ix_audit_logs_user_id"):
            op.create_index("ix_audit_logs_user_id", "audit_logs", ["user_id"], unique=False)

        # старые колонки удаляем только если они реально есть
        insp = inspect(bind)
        if _col_exists(insp, "audit_logs", "object_type"):
            op.drop_column("audit_logs", "object_type")
        if _col_exists(insp, "audit_logs", "meta"):
            op.drop_column("audit_logs", "meta")
        if _col_exists(insp, "audit_logs", "object_id"):
            op.drop_column("audit_logs", "object_id")

    # ---------------------------------------------------------------------
    # 2) bans.reason -> NOT NULL (только если безопасно)
    # ---------------------------------------------------------------------
    if _table_exists(insp, "bans") and _col_exists(insp, "bans", "reason"):
        # если есть NULL — сначала заполняем, чтобы ALTER не упал
        nulls = bind.execute(text("SELECT COUNT(*) FROM bans WHERE reason IS NULL")).scalar() or 0
        if nulls > 0:
            bind.execute(text("UPDATE bans SET reason = '' WHERE reason IS NULL"))

        # теперь можно делать NOT NULL
        op.alter_column("bans", "reason", existing_type=sa.VARCHAR(length=255), nullable=False)

        insp = inspect(bind)
        if not _index_exists(insp, "bans", "ix_bans_user_id"):
            op.create_index("ix_bans_user_id", "bans", ["user_id"], unique=False)

    # ---------------------------------------------------------------------
    # 3) notifications — индексы добавим, но НЕ удаляем старые (не ломаем)
    #    user_id NOT NULL делаем только если NULL'ов нет
    # ---------------------------------------------------------------------
    if _table_exists(insp, "notifications"):
        if _col_exists(insp, "notifications", "user_id"):
            nulls = bind.execute(text("SELECT COUNT(*) FROM notifications WHERE user_id IS NULL")).scalar() or 0
            if nulls == 0:
                op.alter_column("notifications", "user_id", existing_type=sa.INTEGER(), nullable=False)

        insp = inspect(bind)
        if not _index_exists(insp, "notifications", "ix_notifications_entity_id"):
            op.create_index("ix_notifications_entity_id", "notifications", ["entity_id"], unique=False)
        if not _index_exists(insp, "notifications", "ix_notifications_entity_type"):
            op.create_index("ix_notifications_entity_type", "notifications", ["entity_type"], unique=False)
        if not _index_exists(insp, "notifications", "ix_notifications_type"):
            op.create_index("ix_notifications_type", "notifications", ["type"], unique=False)

    # ---------------------------------------------------------------------
    # 4) settings — ГЛАВНЫЙ ФИКС ЭТАПА 11:
    #    id NOT NULL + DEFAULT nextval + sequence + setval
    # ---------------------------------------------------------------------
    if _table_exists(insp, "settings"):
        # ключ/описание — безопасные изменения типов
        if _col_exists(insp, "settings", "key"):
            # если было VARCHAR(100) -> делаем 150
            op.alter_column(
                "settings",
                "key",
                existing_type=sa.VARCHAR(length=100),
                type_=sa.String(length=150),
                existing_nullable=False,
            )

        if _col_exists(insp, "settings", "description"):
            op.alter_column(
                "settings",
                "description",
                existing_type=sa.VARCHAR(length=255),
                type_=sa.Text(),
                existing_nullable=True,
            )

        # created_at / updated_at
        insp = inspect(bind)
        if not _col_exists(insp, "settings", "created_at"):
            op.add_column(
                "settings",
                sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            )
        if not _col_exists(insp, "settings", "updated_at"):
            op.add_column(
                "settings",
                sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            )

        # sequence + id + default
        op.execute("CREATE SEQUENCE IF NOT EXISTS settings_id_seq;")

        insp = inspect(bind)
        if not _col_exists(insp, "settings", "id"):
            # Добавляем id сразу с DEFAULT, чтобы не было твоей ошибки "null in id"
            op.add_column(
                "settings",
                sa.Column("id", sa.Integer(), server_default=sa.text("nextval('settings_id_seq')"), nullable=False),
            )
            # После добавления — можно оставить DEFAULT, это нужно для будущих INSERT'ов.
        else:
            # если id уже есть — ставим DEFAULT и заполняем NULL'ы
            op.execute("ALTER TABLE settings ALTER COLUMN id SET DEFAULT nextval('settings_id_seq');")
            op.execute("UPDATE settings SET id = nextval('settings_id_seq') WHERE id IS NULL;")

        # выравниваем sequence на max(id)+1
        op.execute(
            "SELECT setval('settings_id_seq', COALESCE((SELECT MAX(id) FROM settings), 0) + 1, false);"
        )

        # индексы
        insp = inspect(bind)
        if not _index_exists(insp, "settings", "ix_settings_id"):
            op.create_index("ix_settings_id", "settings", ["id"], unique=False)
        # unique на key может уже быть как PK — но отдельный unique-index не мешает
        if not _index_exists(insp, "settings", "ix_settings_key"):
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

        insp = inspect(bind)
        if _col_exists(insp, "settings", "updated_at"):
            op.drop_column("settings", "updated_at")
        if _col_exists(insp, "settings", "created_at"):
            op.drop_column("settings", "created_at")
        if _col_exists(insp, "settings", "id"):
            op.drop_column("settings", "id")

        op.execute("DROP SEQUENCE IF EXISTS settings_id_seq;")

        # типы обратно
        if _col_exists(insp, "settings", "description"):
            op.alter_column(
                "settings",
                "description",
                existing_type=sa.Text(),
                type_=sa.VARCHAR(length=255),
                existing_nullable=True,
            )
        if _col_exists(insp, "settings", "key"):
            op.alter_column(
                "settings",
                "key",
                existing_type=sa.String(length=150),
                type_=sa.VARCHAR(length=100),
                existing_nullable=False,
            )

    # notifications — откатывать индексы не обязательно, но можно
    if _table_exists(insp, "notifications"):
        insp = inspect(bind)
        if _index_exists(insp, "notifications", "ix_notifications_type"):
            op.drop_index("ix_notifications_type", table_name="notifications")
        if _index_exists(insp, "notifications", "ix_notifications_entity_type"):
            op.drop_index("ix_notifications_entity_type", table_name="notifications")
        if _index_exists(insp, "notifications", "ix_notifications_entity_id"):
            op.drop_index("ix_notifications_entity_id", table_name="notifications")

        # user_id обратно nullable=True (если хочешь строго)
        if _col_exists(insp, "notifications", "user_id"):
            op.alter_column("notifications", "user_id", existing_type=sa.INTEGER(), nullable=True)

    # bans.reason обратно nullable=True
    if _table_exists(insp, "bans") and _col_exists(insp, "bans", "reason"):
        insp = inspect(bind)
        if _index_exists(insp, "bans", "ix_bans_user_id"):
            op.drop_index("ix_bans_user_id", table_name="bans")
        op.alter_column("bans", "reason", existing_type=sa.VARCHAR(length=255), nullable=True)

    # audit_logs
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

        # возвращаем старые колонки (чтобы downgrade был честным)
        insp = inspect(bind)
        if not _col_exists(insp, "audit_logs", "object_id"):
            op.add_column("audit_logs", sa.Column("object_id", sa.Integer(), nullable=True))
        if not _col_exists(insp, "audit_logs", "meta"):
            op.add_column("audit_logs", sa.Column("meta", sa.Text(), nullable=True))
        if not _col_exists(insp, "audit_logs", "object_type"):
            op.add_column("audit_logs", sa.Column("object_type", sa.String(length=50), nullable=True))

        insp = inspect(bind)
        if _col_exists(insp, "audit_logs", "updated_at"):
            op.drop_column("audit_logs", "updated_at")
        if _col_exists(insp, "audit_logs", "user_agent"):
            op.drop_column("audit_logs", "user_agent")
        if _col_exists(insp, "audit_logs", "ip"):
            op.drop_column("audit_logs", "ip")
        if _col_exists(insp, "audit_logs", "data"):
            op.drop_column("audit_logs", "data")
        if _col_exists(insp, "audit_logs", "entity_id"):
            op.drop_column("audit_logs", "entity_id")
        if _col_exists(insp, "audit_logs", "entity"):
            op.drop_column("audit_logs", "entity")

    # debts в downgrade не трогаем — это отдельная миграция restore_debts
