from dataclasses import dataclass

from app.db.models import MetaColumn, MetaTable


@dataclass(frozen=True)
class EditCapabilities:
    """Что можно делать со строками таблицы и почему нельзя, если нельзя."""

    can_update: bool
    can_insert: bool
    can_delete: bool
    read_only_reason: str | None
    primary_key: MetaColumn | None


def edit_capabilities(meta_table: MetaTable) -> EditCapabilities:
    """Итоговые права на строки таблицы по флагам и первичному ключу."""
    pk_columns = [column for column in meta_table.meta_columns if column.is_active and column.is_primary_key]
    if not meta_table.is_editable:
        reason = "Редактирование таблицы выключено"
    elif len(pk_columns) == 0:
        reason = "У таблицы нет первичного ключа — строку нечем адресовать"
    elif len(pk_columns) > 1:
        reason = "Составной первичный ключ пока не поддерживается"
    elif not pk_columns[0].is_visible:
        reason = "Колонка первичного ключа скрыта — клиент не сможет указать строку"
    else:
        reason = None
    editable = reason is None
    return EditCapabilities(
        can_update=editable,
        can_insert=editable and meta_table.allow_insert,
        can_delete=editable and meta_table.allow_delete,
        read_only_reason=reason,
        primary_key=pk_columns[0] if len(pk_columns) == 1 else None,
    )


def column_is_editable(capabilities: EditCapabilities, column: MetaColumn) -> bool:
    """Можно ли менять значение колонки в существующей строке."""
    return capabilities.can_update and column.is_editable and not column.is_primary_key


def column_is_insertable(capabilities: EditCapabilities, column: MetaColumn) -> bool:
    """Можно ли задать колонку при добавлении строки."""
    if not capabilities.can_insert:
        return False
    if column.is_primary_key:
        return not column.is_autoincrement
    return column.is_editable


def column_is_required(column: MetaColumn) -> bool:
    """Без значения добавление не пройдёт: NOT NULL, без default и не генерируется БД."""
    return not column.is_nullable and column.default_value is None and not column.is_autoincrement
