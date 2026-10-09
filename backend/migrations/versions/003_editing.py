"""Редактирование: флаги, сведения о колонках, консоль, журнал

Revision ID: 0003
Revises: 0002
Create Date: 2026-10-09

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def flag_column(name: str, default: str) -> sa.Column:
    """Булев флаг с серверным значением по умолчанию."""
    return sa.Column(name, sa.Boolean(), server_default=sa.text(default), nullable=False)


def upgrade() -> None:
    """Добавляет всё, что нужно для редактирования данных источника."""
    op.add_column("data_source", sa.Column("console_username", sa.String(255), nullable=True))
    op.add_column("data_source", sa.Column("console_password_encrypted", sa.Text(), nullable=True))

    op.add_column("meta_table", flag_column("is_editable", "false"))
    op.add_column("meta_table", flag_column("allow_insert", "false"))
    op.add_column("meta_table", flag_column("allow_delete", "false"))

    op.add_column("meta_column", flag_column("is_editable", "false"))
    op.add_column("meta_column", flag_column("is_nullable", "true"))
    op.add_column("meta_column", sa.Column("default_value", sa.Text(), nullable=True))
    op.add_column("meta_column", flag_column("is_autoincrement", "false"))

    op.create_table(
        "change_log",
        sa.Column("id", sa.BigInteger(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("data_source_id", sa.Integer(), nullable=True),
        sa.Column("meta_table_id", sa.Integer(), nullable=True),
        sa.Column("action", sa.String(20), nullable=False),
        sa.Column("row_key", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("old_values", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("new_values", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("sql_text", sa.Text(), nullable=True),
        sa.Column("affected_rows", sa.Integer(), nullable=True),
        sa.Column("message", sa.Text(), nullable=True),
        sa.Column("client_address", sa.String(100), nullable=True),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_change_log")),
        sa.ForeignKeyConstraint(
            ["data_source_id"],
            ["data_source.id"],
            name=op.f("fk_change_log_data_source_id_data_source"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["meta_table_id"],
            ["meta_table.id"],
            name=op.f("fk_change_log_meta_table_id_meta_table"),
            ondelete="SET NULL",
        ),
        sa.CheckConstraint(
            "action IN ('update', 'insert', 'delete', 'sql_select', 'sql_preview', 'sql_write', 'sql_rejected')",
            name=op.f("ck_change_log_action"),
        ),
    )
    op.create_index(op.f("ix_change_log_data_source_id"), "change_log", ["data_source_id"])
    op.create_index(op.f("ix_change_log_meta_table_id"), "change_log", ["meta_table_id"])


def downgrade() -> None:
    """Убирает всё, что добавила upgrade."""
    op.drop_index(op.f("ix_change_log_meta_table_id"), table_name="change_log")
    op.drop_index(op.f("ix_change_log_data_source_id"), table_name="change_log")
    op.drop_table("change_log")

    op.drop_column("meta_column", "is_autoincrement")
    op.drop_column("meta_column", "default_value")
    op.drop_column("meta_column", "is_nullable")
    op.drop_column("meta_column", "is_editable")

    op.drop_column("meta_table", "allow_delete")
    op.drop_column("meta_table", "allow_insert")
    op.drop_column("meta_table", "is_editable")

    op.drop_column("data_source", "console_password_encrypted")
    op.drop_column("data_source", "console_username")
