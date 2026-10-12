from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.db.models import MetaTable
from app.schemas.admin import AdminColumnOut, AdminTableDetailOut, AdminTableIn, AdminTableOut
from app.services.edit_rules import primary_key_problem


class AdminValidationError(Exception):
    """Настройки не подходят к таблице: например, прислан не тот набор колонок."""


def list_all_tables(session: Session, source_id: int | None) -> list[MetaTable]:
    """Все таблицы, включая скрытые и неактивные; можно сузить до одного источника."""
    statement = (
        select(MetaTable)
        .options(selectinload(MetaTable.meta_columns))
        .order_by(MetaTable.table_name)
    )
    if source_id is not None:
        statement = statement.where(MetaTable.data_source_id == source_id)
    return list(session.scalars(statement))


def get_any_table(session: Session, table_id: int) -> MetaTable | None:
    """Таблица с колонками независимо от видимости; None — если такой нет."""
    statement = (
        select(MetaTable)
        .where(MetaTable.id == table_id)
        .options(selectinload(MetaTable.meta_columns))
    )
    return session.scalar(statement)


def to_admin_table_out(meta_table: MetaTable) -> AdminTableOut:
    """Таблица для списка в админке."""
    return AdminTableOut(
        id=meta_table.id,
        source_id=meta_table.data_source_id,
        schema_name=meta_table.schema_name,
        name=meta_table.table_name,
        label=meta_table.label,
        is_visible=meta_table.is_visible,
        is_active=meta_table.is_active,
        is_editable=meta_table.is_editable,
        allow_insert=meta_table.allow_insert,
        allow_delete=meta_table.allow_delete,
        primary_key_problem=primary_key_problem(meta_table),
    )


def to_admin_table_detail_out(meta_table: MetaTable) -> AdminTableDetailOut:
    """Таблица со всеми колонками для экрана настройки."""
    columns = [
        AdminColumnOut(
            id=column.id,
            name=column.column_name,
            label=column.label,
            data_type=column.data_type,
            type_group=column.type_group,
            position=column.position,
            is_visible=column.is_visible,
            is_filterable=column.is_filterable,
            is_editable=column.is_editable,
            is_primary_key=column.is_primary_key,
            is_nullable=column.is_nullable,
            is_autoincrement=column.is_autoincrement,
            default_value=column.default_value,
            is_active=column.is_active,
        )
        for column in meta_table.meta_columns
    ]
    return AdminTableDetailOut(**to_admin_table_out(meta_table).model_dump(), columns=columns)


def empty_to_none(value: str | None) -> str | None:
    """Пустая подпись — значит, показывать техническое имя."""
    if value is None or value == "":
        return None
    return value


def update_table_settings(session: Session, meta_table: MetaTable, table_in: AdminTableIn) -> MetaTable:
    """Сохраняет настройки таблицы и колонок; позиции колонок — по порядку в запросе."""
    columns_by_id = {column.id: column for column in meta_table.meta_columns}
    received_ids = [column_in.id for column_in in table_in.columns]
    if len(set(received_ids)) != len(received_ids) or set(received_ids) != set(columns_by_id):
        raise AdminValidationError(
            "Нужно прислать все колонки таблицы ровно по одному разу — обновите страницу, если схема менялась"
        )

    meta_table.label = empty_to_none(table_in.label)
    meta_table.is_visible = table_in.is_visible
    meta_table.is_editable = table_in.is_editable
    meta_table.allow_insert = table_in.allow_insert
    meta_table.allow_delete = table_in.allow_delete
    for position, column_in in enumerate(table_in.columns, start=1):
        column = columns_by_id[column_in.id]
        column.label = empty_to_none(column_in.label)
        column.is_visible = column_in.is_visible
        column.is_filterable = column_in.is_filterable
        column.is_editable = column_in.is_editable
        column.position = position
    session.commit()
    # После commit объекты устарели — перечитываем, чтобы колонки встали в новом порядке
    return get_any_table(session, meta_table.id)
