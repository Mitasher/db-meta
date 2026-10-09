from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any

from sqlalchemy import Engine, Select, column as sql_column, func, select, table as sql_table
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.sql.expression import ColumnElement, TableClause

from app.db.models import MetaColumn, MetaTable
from app.schemas.tables import DataPageOut, DataQueryIn, FilterIn, SortIn
from app.services.table_meta import visible_columns
from app.services.type_groups import allowed_operators


class QueryValidationError(Exception):
    """В запросе неизвестная колонка, неподходящий оператор или значение не того типа."""


class SourceQueryError(Exception):
    """Источник не ответил или вернул ошибку."""


def require_column(columns_by_name: dict[str, MetaColumn], name: str) -> MetaColumn:
    """Колонка по имени из разрешённых; это и есть белый список имён."""
    meta_column = columns_by_name.get(name)
    if meta_column is None:
        raise QueryValidationError(f"Колонки {name} нет среди доступных")
    return meta_column


def build_source_table(meta_table: MetaTable) -> TableClause:
    """Описание таблицы источника для конструктора SQL: имена — только из метаданных, все активные колонки."""
    return sql_table(
        meta_table.table_name,
        *(sql_column(column.column_name) for column in meta_table.meta_columns if column.is_active),
        schema=meta_table.schema_name,
    )


def parse_scalar(value: Any, meta_column: MetaColumn) -> Any:
    """Приводит значение из JSON к типу колонки."""
    name = meta_column.column_name
    group = meta_column.type_group
    error = QueryValidationError(f"Колонка {name} ({group}): значение {value!r} не подходит по типу")
    if value is None:
        raise QueryValidationError(f"Колонка {name}: нет значения, для проверки на NULL есть is_null")
    # bool в Python — подкласс int: true/false не должны проходить как число, а числа — как bool
    if isinstance(value, bool) != (group == "boolean"):
        raise error
    if group == "boolean":
        return value
    if group == "string" and isinstance(value, str):
        return value
    if group == "integer":
        if isinstance(value, int):
            return value
        if isinstance(value, str):
            try:
                return int(value)
            except ValueError:
                raise error from None
    if group == "number" and isinstance(value, (int, float, str)):
        try:
            number = Decimal(str(value))
        except InvalidOperation:
            raise error from None
        if number.is_finite():
            return number
    if group == "date" and isinstance(value, str):
        try:
            return date.fromisoformat(value)
        except ValueError:
            raise error from None
    if group == "datetime" and isinstance(value, str):
        try:
            return datetime.fromisoformat(value)
        except ValueError:
            raise error from None
    raise error


def parse_list(value: Any, meta_column: MetaColumn, min_items: int, max_items: int) -> list[Any]:
    """Список значений для between и in."""
    if not isinstance(value, list) or not min_items <= len(value) <= max_items:
        if min_items == max_items:
            expected = f"ровно {min_items}"
        else:
            expected = f"от {min_items} до {max_items}"
        raise QueryValidationError(f"Колонка {meta_column.column_name}: нужен список, в нём {expected} значений")
    return [parse_scalar(item, meta_column) for item in value]


def build_condition(column: ColumnElement, meta_column: MetaColumn, filter_in: FilterIn) -> ColumnElement:
    """Условие WHERE из одного фильтра; значения уходят в запрос параметрами."""
    name = meta_column.column_name
    operator = filter_in.operator
    if not meta_column.is_filterable:
        raise QueryValidationError(f"По колонке {name} фильтровать нельзя")
    if operator not in allowed_operators(meta_column.type_group):
        raise QueryValidationError(
            f"Оператор {operator} недоступен для колонки {name} ({meta_column.type_group})"
        )
    if operator in ("is_null", "is_not_null"):
        if filter_in.value is not None:
            raise QueryValidationError(f"Колонка {name}: у оператора {operator} не бывает значения")
        if operator == "is_null":
            return column.is_(None)
        return column.is_not(None)
    if operator == "between":
        low, high = parse_list(filter_in.value, meta_column, 2, 2)
        return column.between(low, high)
    if operator == "in":
        # Потолок, чтобы один фильтр не превратился в запрос с десятками тысяч параметров
        return column.in_(parse_list(filter_in.value, meta_column, 1, 1000))
    value = parse_scalar(filter_in.value, meta_column)
    if operator == "eq":
        return column == value
    if operator == "ne":
        return column != value
    if operator == "gt":
        return column > value
    if operator == "lt":
        return column < value
    if operator == "like":
        return column.like(value)
    raise QueryValidationError(f"Неизвестный оператор {operator}")


def select_columns(
    requested: list[str] | None,
    columns_by_name: dict[str, MetaColumn],
    shown: list[MetaColumn],
) -> list[MetaColumn]:
    """Колонки для SELECT: запрошенные в их порядке или все видимые."""
    if not requested:
        return shown
    selected = []
    for name in requested:
        meta_column = require_column(columns_by_name, name)
        if meta_column not in selected:
            selected.append(meta_column)
    return selected


def build_order_by(
    source_table: TableClause,
    columns_by_name: dict[str, MetaColumn],
    active: list[MetaColumn],
    sort: list[SortIn],
) -> list[ColumnElement]:
    """ORDER BY из запроса, добитый первичным ключом — чтобы строки не переезжали между страницами."""
    order_by = []
    used = set()
    for sort_in in sort:
        meta_column = require_column(columns_by_name, sort_in.column)
        if meta_column.column_name in used:
            continue
        used.add(meta_column.column_name)
        column = source_table.c[meta_column.column_name]
        order_by.append(column.desc() if sort_in.direction == "desc" else column.asc())
    for meta_column in active:
        if meta_column.is_primary_key and meta_column.column_name not in used:
            order_by.append(source_table.c[meta_column.column_name].asc())
    return order_by

@dataclass(frozen=True)
class PageStatements:
    """Готовые запросы страницы: подсчёт строк и сами строки."""

    count: Select
    data: Select
    column_names: list[str]


def build_page_statements(meta_table: MetaTable, query: DataQueryIn) -> PageStatements:
    """Проверяет запрос по метаданным и собирает SQL; в источник не ходит."""
    shown = visible_columns(meta_table)
    if not shown:
        raise QueryValidationError("У таблицы нет видимых колонок")
    columns_by_name = {column.column_name: column for column in shown}
    selected = select_columns(query.columns, columns_by_name, shown)

    # Все активные колонки, включая скрытые PK: по ним добивается сортировка
    active = [column for column in meta_table.meta_columns if column.is_active]
    source_table = build_source_table(meta_table)

    conditions = []
    for filter_in in query.filters:
        meta_column = require_column(columns_by_name, filter_in.column)
        conditions.append(build_condition(source_table.c[meta_column.column_name], meta_column, filter_in))
    order_by = build_order_by(source_table, columns_by_name, active, query.sort)

    return PageStatements(
        count=select(func.count()).select_from(source_table).where(*conditions),
        data=(
            select(*(source_table.c[column.column_name] for column in selected))
            .where(*conditions)
            .order_by(*order_by)
            .limit(query.page_size)
            .offset((query.page - 1) * query.page_size)
        ),
        column_names=[column.column_name for column in selected],
    )


def fetch_page(engine: Engine, meta_table: MetaTable, query: DataQueryIn) -> DataPageOut:
    """Страница данных таблицы источника по фильтрам, сортировке и пагинации."""
    statements = build_page_statements(meta_table, query)
    try:
        with engine.connect() as connection:
            total = connection.execute(statements.count).scalar_one()
            rows = [dict(row._mapping) for row in connection.execute(statements.data)]
    except SQLAlchemyError as error:
        raise SourceQueryError(
            f"Ошибка запроса к источнику: {error}. Если схема источника менялась — запустите синхронизацию"
        ) from error

    return DataPageOut(
        columns=statements.column_names,
        rows=rows,
        total=total,
        page=query.page,
        page_size=query.page_size,
    )

