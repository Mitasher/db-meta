from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload, selectinload

from app.db.models import MetaColumn, MetaTable
from app.schemas.tables import ColumnOut, TableMetaOut, TableOut
from app.services.type_groups import allowed_operators


def list_visible_tables(session: Session, source_id: int | None) -> list[MetaTable]:
    """Видимые и активные таблицы по имени; можно сузить до одного источника."""
    statement = (
        select(MetaTable)
        .where(MetaTable.is_visible.is_(True), MetaTable.is_active.is_(True))
        .order_by(MetaTable.table_name)
    )
    if source_id is not None:
        statement = statement.where(MetaTable.data_source_id == source_id)
    return list(session.scalars(statement))


def get_visible_table(session: Session, table_id: int) -> MetaTable | None:
    """Видимая и активная таблица с колонками и источником; None — если такой нет."""
    statement = (
        select(MetaTable)
        .where(
            MetaTable.id == table_id,
            MetaTable.is_visible.is_(True),
            MetaTable.is_active.is_(True),
        )
        .options(selectinload(MetaTable.meta_columns), joinedload(MetaTable.data_source))
    )
    return session.scalar(statement)


def visible_columns(meta_table: MetaTable) -> list[MetaColumn]:
    """Активные и видимые колонки по порядку."""
    return [column for column in meta_table.meta_columns if column.is_active and column.is_visible]


def to_table_out(meta_table: MetaTable) -> TableOut:
    """Таблица для списка."""
    return TableOut(
        id=meta_table.id,
        source_id=meta_table.data_source_id,
        schema_name=meta_table.schema_name,
        name=meta_table.table_name,
        label=meta_table.label or meta_table.table_name,
    )


def to_table_meta_out(meta_table: MetaTable) -> TableMetaOut:
    """Таблица с колонками — контракт для фронта."""
    columns = [
        ColumnOut(
            id=column.id,
            name=column.column_name,
            label=column.label or column.column_name,
            data_type=column.data_type,
            type_group=column.type_group,
            is_primary_key=column.is_primary_key,
            is_filterable=column.is_filterable,
            operators=allowed_operators(column.type_group) if column.is_filterable else [],
        )
        for column in visible_columns(meta_table)
    ]
    return TableMetaOut(**to_table_out(meta_table).model_dump(), columns=columns)
