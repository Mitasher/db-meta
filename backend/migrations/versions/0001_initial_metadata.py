"""Начальная схема метаданных"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def timestamp_columns() -> list[sa.Column]:
    """Колонки created_at и updated_at."""
    return [
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    ]


def upgrade() -> None:
    """Создаёт таблицы метаданных."""
    op.create_table(
        "data_source",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("db_type", sa.String(20), nullable=False),
        sa.Column("host", sa.String(255), nullable=False),
        sa.Column("port", sa.Integer(), nullable=False),
        sa.Column("database", sa.String(255), nullable=False),
        sa.Column("username", sa.String(255), nullable=False),
        sa.Column("password_encrypted", sa.Text(), nullable=False),
        sa.Column("last_synced_at", sa.DateTime(timezone=True), nullable=True),
        *timestamp_columns(),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_data_source")),
        sa.UniqueConstraint("name", name=op.f("uq_data_source_name")),
        sa.CheckConstraint("db_type IN ('postgresql', 'mysql')", name=op.f("ck_data_source_db_type")),
    )

    op.create_table(
        "meta_table",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("data_source_id", sa.Integer(), nullable=False),
        sa.Column("schema_name", sa.String(255), nullable=False),
        sa.Column("table_name", sa.String(255), nullable=False),
        sa.Column("label", sa.String(255), nullable=True),
        sa.Column("is_visible", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        *timestamp_columns(),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_meta_table")),
        sa.ForeignKeyConstraint(
            ["data_source_id"],
            ["data_source.id"],
            name=op.f("fk_meta_table_data_source_id_data_source"),
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint(
            "data_source_id",
            "schema_name",
            "table_name",
            name=op.f("uq_meta_table_data_source_id_schema_name_table_name"),
        ),
    )

    op.create_table(
        "meta_column",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("meta_table_id", sa.Integer(), nullable=False),
        sa.Column("column_name", sa.String(255), nullable=False),
        sa.Column("data_type", sa.String(255), nullable=False),
        sa.Column("label", sa.String(255), nullable=True),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("is_visible", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("is_primary_key", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("is_filterable", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        *timestamp_columns(),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_meta_column")),
        sa.ForeignKeyConstraint(
            ["meta_table_id"],
            ["meta_table.id"],
            name=op.f("fk_meta_column_meta_table_id_meta_table"),
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint(
            "meta_table_id",
            "column_name",
            name=op.f("uq_meta_column_meta_table_id_column_name"),
        ),
    )

    op.create_table(
        "query_template",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("meta_table_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("body", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        *timestamp_columns(),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_query_template")),
        sa.ForeignKeyConstraint(
            ["meta_table_id"],
            ["meta_table.id"],
            name=op.f("fk_query_template_meta_table_id_meta_table"),
            ondelete="RESTRICT",
        ),
    )
    op.create_index(op.f("ix_query_template_meta_table_id"), "query_template", ["meta_table_id"])


def downgrade() -> None:
    """Удаляет таблицы метаданных."""
    op.drop_index(op.f("ix_query_template_meta_table_id"), table_name="query_template")
    op.drop_table("query_template")
    op.drop_table("meta_column")
    op.drop_table("meta_table")
    op.drop_table("data_source")
