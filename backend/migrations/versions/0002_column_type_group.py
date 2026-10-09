"""Группа типа колонки

Revision ID: 0002
Revises: 0001
Create Date: 2026-10-09

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Добавляет meta_column.type_group; значения проставит следующая синхронизация."""
    op.add_column(
        "meta_column",
        sa.Column("type_group", sa.String(20), server_default=sa.text("'other'"), nullable=False),
    )
    op.create_check_constraint(
        op.f("ck_meta_column_type_group"),
        "meta_column",
        "type_group IN ('string', 'integer', 'number', 'date', 'datetime', 'boolean', 'other')",
    )


def downgrade() -> None:
    """Убирает meta_column.type_group."""
    op.drop_constraint(op.f("ck_meta_column_type_group"), "meta_column", type_="check")
    op.drop_column("meta_column", "type_group")
