from datetime import date, datetime, time
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import ChangeLog


def json_safe(value: Any) -> Any:
    """Значение из БД в вид, который ложится в JSONB и в ответ API."""
    if isinstance(value, (datetime, date, time)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, (bytes, bytearray)):
        return "0x" + bytes(value).hex()
    return value


def json_safe_dict(values: dict[str, Any] | None) -> dict[str, Any] | None:
    """json_safe для всех значений словаря."""
    if values is None:
        return None
    return {key: json_safe(value) for key, value in values.items()}


def add_change(
    session: Session,
    *,
    action: str,
    data_source_id: int | None,
    meta_table_id: int | None = None,
    row_key: dict[str, Any] | None = None,
    old_values: dict[str, Any] | None = None,
    new_values: dict[str, Any] | None = None,
    sql_text: str | None = None,
    affected_rows: int | None = None,
    message: str | None = None,
    client_address: str | None = None,
) -> None:
    """Записывает действие в журнал и сразу фиксирует."""
    session.add(
        ChangeLog(
            action=action,
            data_source_id=data_source_id,
            meta_table_id=meta_table_id,
            row_key=json_safe_dict(row_key),
            old_values=json_safe_dict(old_values),
            new_values=json_safe_dict(new_values),
            sql_text=sql_text,
            affected_rows=affected_rows,
            message=message,
            client_address=client_address,
        )
    )
    session.commit()


def list_changes(
    session: Session,
    table_id: int | None,
    source_id: int | None,
    limit: int,
    before_id: int | None,
) -> list[ChangeLog]:
    """Записи журнала от новых к старым; before_id — для следующей порции."""
    statement = select(ChangeLog).order_by(ChangeLog.id.desc()).limit(limit)
    if table_id is not None:
        statement = statement.where(ChangeLog.meta_table_id == table_id)
    if source_id is not None:
        statement = statement.where(ChangeLog.data_source_id == source_id)
    if before_id is not None:
        statement = statement.where(ChangeLog.id < before_id)
    return list(session.scalars(statement))
