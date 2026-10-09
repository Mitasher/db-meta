from dataclasses import dataclass
from typing import Any

from sqlalchemy import Engine, delete, insert, select, update
from sqlalchemy.engine import Connection
from sqlalchemy.exc import DataError, IntegrityError, SQLAlchemyError
from sqlalchemy.sql.expression import ColumnElement, TableClause

from app.db.models import MetaColumn, MetaTable
from app.schemas.rows import RowInsertIn, RowUpdateIn
from app.services.edit_rules import (
    EditCapabilities,
    column_is_editable,
    column_is_insertable,
    column_is_required,
    edit_capabilities,
)
from app.services.table_data import (
    QueryValidationError,
    SourceQueryError,
    build_source_table,
    parse_scalar,
    require_column,
)
from app.services.table_meta import visible_columns


class EditForbiddenError(Exception):
    """Таблица или колонка закрыта для правки."""


class RowNotFoundError(Exception):
    """Строки с таким ключом нет."""


class RowConflictError(Exception):
    """Строку успели изменить: исходные значения не совпали."""


class SourceConstraintError(Exception):
    """Источник отклонил изменение: внешний ключ, уникальность, CHECK."""


@dataclass(frozen=True)
class RowChange:
    """Итог правки: ключ строки, что было, что стало, и строка после записи."""

    key: dict[str, Any]
    old_values: dict[str, Any] | None
    new_values: dict[str, Any] | None
    row: dict[str, Any] | None


def parse_new_value(value: Any, column: MetaColumn) -> Any:
    """Новое значение колонки: NULL — только для nullable, остальное приводится к типу."""
    if value is None:
        if not column.is_nullable:
            raise QueryValidationError(f"Колонка {column.column_name} не может быть пустой")
        return None
    return parse_scalar(value, column)


def parse_original_value(value: Any, column: MetaColumn) -> Any:
    """Исходное значение для сверки: NULL допустим всегда — так могло быть в БД."""
    if value is None:
        return None
    return parse_scalar(value, column)


def equals(column: ColumnElement, value: Any) -> ColumnElement:
    """Условие «колонка равна значению» с учётом NULL."""
    if value is None:
        return column.is_(None)
    return column == value


def primary_key_of(capabilities: EditCapabilities, pk_raw: str) -> tuple[MetaColumn, Any]:
    """Колонка PK и значение ключа из URL, приведённое к её типу."""
    pk = capabilities.primary_key
    if pk is None:
        raise EditForbiddenError(capabilities.read_only_reason or "У таблицы нет первичного ключа")
    return pk, parse_scalar(pk_raw, pk)


def read_row(
    connection: Connection,
    table: TableClause,
    pk: MetaColumn,
    pk_value: Any,
    columns: list[MetaColumn],
) -> dict[str, Any] | None:
    """Строка по первичному ключу, только переданные колонки."""
    statement = select(*(table.c[column.column_name] for column in columns)).where(
        table.c[pk.column_name] == pk_value
    )
    row = connection.execute(statement).first()
    if row is None:
        return None
    return dict(row._mapping)


def translate_source_error(error: SQLAlchemyError) -> Exception:
    """Ошибка источника → понятное исключение для API."""
    if isinstance(error, IntegrityError):
        return SourceConstraintError(f"Источник отклонил изменение — нарушено ограничение: {error.orig}")
    if isinstance(error, DataError):
        return QueryValidationError(f"Источник отклонил значение: {error.orig}")
    return SourceQueryError(f"Ошибка запроса к источнику: {error}")


def update_row(engine: Engine, meta_table: MetaTable, pk_raw: str, update_in: RowUpdateIn) -> RowChange:
    """Меняет поля одной строки, если их никто не изменил с момента чтения."""
    capabilities = edit_capabilities(meta_table)
    if not capabilities.can_update:
        raise EditForbiddenError(capabilities.read_only_reason or "Изменение строк выключено")
    if not update_in.changes:
        raise QueryValidationError("Нет изменённых полей")
    if set(update_in.original) != set(update_in.changes):
        raise QueryValidationError("В original нужны исходные значения ровно тех полей, что меняются")
    pk, pk_value = primary_key_of(capabilities, pk_raw)

    shown = visible_columns(meta_table)
    columns_by_name = {column.column_name: column for column in shown}
    new_values = {}
    old_values = {}
    for name, value in update_in.changes.items():
        column = require_column(columns_by_name, name)
        if not column_is_editable(capabilities, column):
            raise EditForbiddenError(f"Колонку {name} менять нельзя")
        new_values[name] = parse_new_value(value, column)
        old_values[name] = parse_original_value(update_in.original[name], column)

    table = build_source_table(meta_table)
    # Исходные значения в WHERE: если строку уже поменяли, UPDATE её не найдёт — защита от потерянного обновления
    conditions = [table.c[pk.column_name] == pk_value]
    conditions.extend(equals(table.c[name], value) for name, value in old_values.items())
    statement = (
        update(table)
        .where(*conditions)
        .values({table.c[name]: value for name, value in new_values.items()})
    )
    try:
        with engine.begin() as connection:
            # MySQL-диалект SQLAlchemy включает CLIENT_FOUND_ROWS: rowcount — найденные строки, а не изменённые
            if connection.execute(statement).rowcount == 0:
                if read_row(connection, table, pk, pk_value, [pk]) is None:
                    raise RowNotFoundError(f"Строки {pk.column_name} = {pk_value} нет")
                raise RowConflictError("Данные изменились, обновите страницу")
            row = read_row(connection, table, pk, pk_value, shown)
    except SQLAlchemyError as error:
        raise translate_source_error(error) from error
    return RowChange(key={pk.column_name: pk_value}, old_values=old_values, new_values=new_values, row=row)


def insert_row(engine: Engine, meta_table: MetaTable, insert_in: RowInsertIn) -> RowChange:
    """Добавляет строку и возвращает её такой, какой её записала БД."""
    capabilities = edit_capabilities(meta_table)
    if not capabilities.can_insert:
        raise EditForbiddenError(capabilities.read_only_reason or "Добавление строк выключено")
    pk = capabilities.primary_key

    shown = visible_columns(meta_table)
    columns_by_name = {column.column_name: column for column in shown}
    values = {}
    for name, value in insert_in.values.items():
        column = require_column(columns_by_name, name)
        if not column_is_insertable(capabilities, column):
            raise EditForbiddenError(f"Колонку {name} при добавлении задавать нельзя")
        values[name] = parse_new_value(value, column)
    missing = [
        column.column_name
        for column in meta_table.meta_columns
        if column.is_active and column_is_required(column) and column.column_name not in values
    ]
    if missing:
        raise QueryValidationError(f"Не заполнены обязательные колонки: {', '.join(missing)}")

    table = build_source_table(meta_table)
    statement = insert(table).values({table.c[name]: value for name, value in values.items()})
    use_returning = pk.column_name not in values and engine.dialect.insert_returning
    if use_returning:
        statement = statement.returning(table.c[pk.column_name])
    try:
        with engine.begin() as connection:
            result = connection.execute(statement)
            if pk.column_name in values:
                pk_value = values[pk.column_name]
            elif use_returning:
                pk_value = result.scalar_one()
            else:
                # MySQL не умеет INSERT ... RETURNING — ключ из AUTO_INCREMENT берём так
                pk_value = result.lastrowid
            row = read_row(connection, table, pk, pk_value, shown)
    except SQLAlchemyError as error:
        raise translate_source_error(error) from error
    return RowChange(key={pk.column_name: pk_value}, old_values=None, new_values=values, row=row)


def delete_row(engine: Engine, meta_table: MetaTable, pk_raw: str) -> RowChange:
    """Удаляет строку; в журнал уходит то, что в ней было."""
    capabilities = edit_capabilities(meta_table)
    if not capabilities.can_delete:
        raise EditForbiddenError(capabilities.read_only_reason or "Удаление строк выключено")
    pk, pk_value = primary_key_of(capabilities, pk_raw)

    shown = visible_columns(meta_table)
    table = build_source_table(meta_table)
    try:
        with engine.begin() as connection:
            old_row = read_row(connection, table, pk, pk_value, shown)
            if old_row is None:
                raise RowNotFoundError(f"Строки {pk.column_name} = {pk_value} нет")
            connection.execute(delete(table).where(table.c[pk.column_name] == pk_value))
    except SQLAlchemyError as error:
        raise translate_source_error(error) from error
    return RowChange(key={pk.column_name: pk_value}, old_values=old_row, new_values=None, row=None)
