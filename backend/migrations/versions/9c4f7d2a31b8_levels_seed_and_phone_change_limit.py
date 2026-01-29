"""Seed production levels + limit phone changes.

This migration does 2 things:
1) Makes levels.sort_order safer by adding a server-side default (0) and normalizes/creates
   the 4 production levels from the TЗ: Новичок, Средний-, Средний, Средний+.
2) Adds users.phone_change_count to enforce "сменить телефон можно только 1 раз"
   (initial set does not count; only change from an existing phone increments the counter).

Revision ID: 9c4f7d2a31b8
Revises: 7e1f74384b83
Create Date: 2026-01-27
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "9c4f7d2a31b8"
down_revision: str | None = "7e1f74384b83"
branch_labels = None
depends_on = None


TARGET_LEVELS = [
    # id, name, description, sort_order
    (1, "Новичок", "Начальный уровень", 10),
    (2, "Средний-", "Уверенный любитель (ниже среднего)", 20),
    (3, "Средний", "Уверенный любитель (средний)", 30),
    (4, "Средний+", "Сильный любитель (выше среднего)", 40),
]


def _norm(s: str) -> str:
    s = (s or "").strip().lower()
    s = s.replace("−", "-")  # unicode minus
    s = "".join(s.split())
    return s


def _map_legacy_to_target(name: str) -> str | None:
    """Map legacy level names (if any) to the 4 target levels."""
    n = _norm(name)
    if not n:
        return None
    # already new
    if "нович" in n:
        return "Новичок"
    if "средний-" in n:
        return "Средний-"
    if n == "средний":
        return "Средний"
    if "средний+" in n:
        return "Средний+"

    # legacy examples (если где-то были старые)
    if "лайтпро" in n or "lightpro" in n or n == "pro" or "медиум" in n or "medium" in n:
        return "Средний+"
    if "лайт+" in n or "light+" in n:
        return "Средний"
    if "лайт" in n or "light" in n or "любитель" in n:
        return "Средний-"
    if "профи" in n:
        return "Средний+"

    return None


def upgrade() -> None:
    conn = op.get_bind()

    # 1) Make sort_order safer: add a server-side default (0), and fix possible NULLs
    op.alter_column(
        "levels",
        "sort_order",
        existing_type=sa.Integer(),
        nullable=False,
        server_default=sa.text("0"),
    )
    conn.execute(sa.text("UPDATE levels SET sort_order = 0 WHERE sort_order IS NULL"))

    # 2) Load existing levels
    rows = conn.execute(sa.text("SELECT id, name FROM levels ORDER BY id")).fetchall()

    # Track which ids are already used
    used_ids = {int(r.id) for r in rows}

    # Canonical IDs for targets (prefer existing by ID, else by name, else by legacy mapping)
    target_name_to_id: dict[str, int] = {}
    extra_ids_to_merge: list[tuple[int, int]] = []  # (old_id, canonical_id)

    # First pass: mark exact matches by name
    for r in rows:
        mapped = _map_legacy_to_target(r.name)
        if mapped in {t[1] for t in TARGET_LEVELS}:
            # if we already have canonical for that name, mark as duplicate
            if mapped in target_name_to_id:
                extra_ids_to_merge.append((int(r.id), int(target_name_to_id[mapped])))
            else:
                target_name_to_id[mapped] = int(r.id)

    # Ensure each target exists; prefer fixed IDs if possible
    for tid, tname, tdesc, tsort in TARGET_LEVELS:
        if tname in target_name_to_id:
            cid = target_name_to_id[tname]
            # normalize existing canonical row
            conn.execute(
                sa.text(
                    "UPDATE levels SET name=:name, description=:desc, sort_order=:sort WHERE id=:id"
                ),
                {"name": tname, "desc": tdesc, "sort": tsort, "id": cid},
            )
            continue

        # If fixed ID exists, reuse it
        if tid in used_ids:
            conn.execute(
                sa.text(
                    "UPDATE levels SET name=:name, description=:desc, sort_order=:sort WHERE id=:id"
                ),
                {"name": tname, "desc": tdesc, "sort": tsort, "id": tid},
            )
            target_name_to_id[tname] = tid
            continue

        # Otherwise insert with fixed ID
        conn.execute(
            sa.text(
                "INSERT INTO levels (id, name, description, sort_order) VALUES (:id, :name, :desc, :sort)"
            ),
            {"id": tid, "name": tname, "desc": tdesc, "sort": tsort},
        )
        used_ids.add(tid)
        target_name_to_id[tname] = tid

    # Merge duplicates: move users.level_id -> canonical_id, then delete duplicate rows
    for old_id, canonical_id in extra_ids_to_merge:
        conn.execute(
            sa.text("UPDATE users SET level_id=:new WHERE level_id=:old"),
            {"new": canonical_id, "old": old_id},
        )
        conn.execute(sa.text("DELETE FROM levels WHERE id=:id"), {"id": old_id})

    # Finally: fix sequence to max(id)
    conn.execute(
        sa.text(
            "SELECT setval(pg_get_serial_sequence('levels','id'), (SELECT COALESCE(MAX(id),1) FROM levels))"
        )
    )

    # 3) Add phone_change_count to users (enforce \"сменить телефон можно только 1 раз\")
    op.add_column(
        "users",
        sa.Column(
            "phone_change_count",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
    )


def downgrade() -> None:
    # rollback phone restriction support
    op.drop_column("users", "phone_change_count")

    # rollback default on sort_order (optional)
    op.alter_column(
        "levels",
        "sort_order",
        existing_type=sa.Integer(),
        nullable=False,
        server_default=None,
    )
