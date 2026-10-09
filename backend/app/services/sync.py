from dataclasses import dataclass, field
from datetime import datetime, timezone

from sqlalchemy import Engine, inspect, select
from sqlalchemy.exc import CompileError, SQLAlchemyError
from sqlalchemy.orm import Session, selectinload
from sqlalchemy.types import TypeEngine

from app.db.models import DataSource, MetaColumn, MetaTable
from app.services.source_connection import create_source_engine
from app.services.type_groups import detect_type_group


class SyncError(Exception):
    """Источник недоступен или его схему не прочитать."""


@dataclass(frozen=True)
class ReflectedColumn:
    """Колонка как в источнике."""
    name: str
    data_type: str
    type_group: str
    position: int
    is_primary_key: bool
    is_nullable: bool
    default_value: str | None
    is_autoincrement: bool



@dataclass(frozen=True)
class ReflectedTable:
    """Таблица как в источнике."""

    name: str
    columns: list[ReflectedColumn]


@dataclass
class SyncCounter:
    """Сколько записей добавлено, обновлено и помечено неактивными."""

    added: int = 0
    updated: int = 0
    deactivated: int = 0


@dataclass
class SyncSummary:
    """Итог синхронизации одного источника."""

    source_id: int
    schema_name: str
    synced_at: datetime
    tables: SyncCounter = field(default_factory=SyncCounter)
    columns: SyncCounter = field(default_factory=SyncCounter)


def describe_type(column_type: TypeEngine) -> str:
    """Тип колонки строкой, как в СУБД."""
    try:
        type_name = str(column_type)
    except CompileError:
        type_name = column_type.__class__.__name__
    # meta_column.data_type — VARCHAR(255)
    return type_name[:255]


def detect_autoincrement(column: dict, default_value: str | None) -> bool:
    """Значение колонки генерирует сама БД: AUTO_INCREMENT, IDENTITY или serial."""
    if column.get("autoincrement") is True:
        return True
    if column.get("identity") is not None:
        return True
    # serial в PostgreSQL — это default nextval(...)
    return default_value is not None and default_value.startswith("nextval(")


def reflect_source(engine: Engine) -> tuple[str, list[ReflectedTable]]:
    """Читает таблицы, колонки и PK схемы по умолчанию."""
    inspector = inspect(engine)
    schema_name = inspector.default_schema_name
    tables = []
    for table_name in sorted(inspector.get_table_names(schema=schema_name)):
        primary_key = set(
            inspector.get_pk_constraint(table_name, schema=schema_name)["constrained_columns"]
        )
        columns = []
        for position, column in enumerate(inspector.get_columns(table_name, schema=schema_name), start=1):
            default = column.get("default")
            default_value = None if default is None else str(default)
            columns.append(
                ReflectedColumn(
                    name=column["name"],
                    data_type=describe_type(column["type"]),
                    type_group=detect_type_group(column["type"]),
                    position=position,
                    is_primary_key=column["name"] in primary_key,
                    is_nullable=bool(column["nullable"]),
                    default_value=default_value,
                    is_autoincrement=detect_autoincrement(column, default_value),
                )
            )
        tables.append(ReflectedTable(name=table_name, columns=columns))
    return schema_name, tables


def assign(target: object, field_name: str, value: object) -> bool:
    """Записывает значение, только по изменению."""
    if getattr(target, field_name) == value:
        return False
    setattr(target, field_name, value)
    return True


def sync_columns(table: MetaTable, reflected_columns: list[ReflectedColumn], counter: SyncCounter) -> None:
    """Сверяет колонки одной таблицы; label, is_visible, is_filterable не трогает."""
    existing = {column.column_name: column for column in table.meta_columns}
    seen = set()
    for reflected in reflected_columns:
        seen.add(reflected.name)
        meta_column = existing.get(reflected.name)
        if meta_column is None:
            table.meta_columns.append(
                MetaColumn(
                    column_name=reflected.name,
                    data_type=reflected.data_type,
                    type_group=reflected.type_group,
                    position=reflected.position,
                    is_primary_key=reflected.is_primary_key,
                    is_nullable=reflected.is_nullable,
                    default_value=reflected.default_value,
                    is_autoincrement=reflected.is_autoincrement,
                )
            )

            counter.added += 1
            continue

        changes = [
            assign(meta_column, "data_type", reflected.data_type),
            assign(meta_column, "type_group", reflected.type_group),
            assign(meta_column, "position", reflected.position),
            assign(meta_column, "is_primary_key", reflected.is_primary_key),
            assign(meta_column, "is_nullable", reflected.is_nullable),
            assign(meta_column, "default_value", reflected.default_value),
            assign(meta_column, "is_autoincrement", reflected.is_autoincrement),
            assign(meta_column, "is_active", True),
        ]

        if any(changes):
            counter.updated += 1
    for name, meta_column in existing.items():
        if name not in seen and meta_column.is_active:
            meta_column.is_active = False
            counter.deactivated += 1


def apply_snapshot(
    session: Session,
    source: DataSource,
    schema_name: str,
    reflected_tables: list[ReflectedTable],
) -> SyncSummary:
    """Сверяет метаданные источника со снимком его схемы."""
    summary = SyncSummary(
        source_id=source.id,
        schema_name=schema_name,
        synced_at=datetime.now(timezone.utc),
    )
    existing_tables = session.scalars(
        select(MetaTable)
        .where(MetaTable.data_source_id == source.id)
        .options(selectinload(MetaTable.meta_columns))
    ).all()
    existing = {(table.schema_name, table.table_name): table for table in existing_tables}
    seen = set()
    for reflected in reflected_tables:
        key = (schema_name, reflected.name)
        seen.add(key)
        table = existing.get(key)
        if table is None:
            table = MetaTable(data_source_id=source.id, schema_name=schema_name, table_name=reflected.name)
            session.add(table)
            summary.tables.added += 1
        elif assign(table, "is_active", True):
            summary.tables.updated += 1
        sync_columns(table, reflected.columns, summary.columns)
    for key, table in existing.items():
        if key not in seen and table.is_active:
            table.is_active = False
            summary.tables.deactivated += 1
    source.last_synced_at = summary.synced_at
    return summary


def sync_source(session: Session, source_id: int, secret_key: str) -> SyncSummary | None:
    """Синхронизирует метаданные источника; None — если источника нет."""

    source = session.get(DataSource, source_id, with_for_update=True)
    if source is None:
        return None
    try:
        engine = create_source_engine(source, secret_key)
    except ValueError as error:
        raise SyncError(str(error)) from error
    try:
        schema_name, reflected_tables = reflect_source(engine)
    except SQLAlchemyError as error:
        raise SyncError(f"Не удалось прочитать схему источника: {error}") from error
    finally:
        engine.dispose()
    summary = apply_snapshot(session, source, schema_name, reflected_tables)
    session.commit()
    return summary
