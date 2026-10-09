from typing import Callable

from fastapi import APIRouter, HTTPException, Request
from sqlalchemy import Engine
from sqlalchemy.orm import Session

from app.api.client import client_address
from app.api.tables import table_not_found
from app.db.models import MetaTable
from app.schemas.rows import RowInsertIn, RowOut, RowUpdateIn
from app.services.change_log import add_change, json_safe_dict
from app.services.engine_cache import SourceEngineCache
from app.services.row_edit import (
    EditForbiddenError,
    RowChange,
    RowConflictError,
    RowNotFoundError,
    SourceConstraintError,
    delete_row,
    insert_row,
    update_row,
)
from app.services.table_data import QueryValidationError, SourceQueryError
from app.services.table_meta import get_visible_table


def create_rows_router(meta_engine: Engine, engine_cache: SourceEngineCache) -> APIRouter:
    """Эндпоинты правки строк источника."""
    router = APIRouter(prefix="/api/tables", tags=["rows"])

    def apply_change(
        table_id: int,
        request: Request,
        action: str,
        operation: Callable[[Engine, MetaTable], RowChange],
    ) -> RowChange:
        """Общий путь правки: найти таблицу, выполнить, перевести ошибки в HTTP, записать в журнал."""
        with Session(meta_engine) as session:
            meta_table = get_visible_table(session, table_id)
            if meta_table is None:
                raise table_not_found(table_id)
            try:
                engine = engine_cache.get(meta_table.data_source)
            except ValueError as error:
                raise HTTPException(status_code=502, detail=str(error)) from error
            try:
                change = operation(engine, meta_table)
            except EditForbiddenError as error:
                raise HTTPException(status_code=403, detail=str(error)) from error
            except QueryValidationError as error:
                raise HTTPException(status_code=400, detail=str(error)) from error
            except RowNotFoundError as error:
                raise HTTPException(status_code=404, detail=str(error)) from error
            except (RowConflictError, SourceConstraintError) as error:
                raise HTTPException(status_code=409, detail=str(error)) from error
            except SourceQueryError as error:
                raise HTTPException(status_code=502, detail=str(error)) from error
            add_change(
                session,
                action=action,
                data_source_id=meta_table.data_source_id,
                meta_table_id=meta_table.id,
                row_key=change.key,
                old_values=change.old_values,
                new_values=change.new_values,
                client_address=client_address(request),
            )
            return change

    @router.patch("/{table_id}/rows/{pk}", response_model=RowOut)
    def update(table_id: int, pk: str, update_in: RowUpdateIn, request: Request) -> RowOut:
        """Меняет поля строки; в ответе — строка, как она теперь лежит в БД."""
        change = apply_change(
            table_id, request, "update", lambda engine, meta_table: update_row(engine, meta_table, pk, update_in)
        )
        return RowOut(row=json_safe_dict(change.row))

    @router.post("/{table_id}/rows", response_model=RowOut, status_code=201)
    def create(table_id: int, insert_in: RowInsertIn, request: Request) -> RowOut:
        """Добавляет строку; в ответе — строка с ключом и значениями по умолчанию из БД."""
        change = apply_change(
            table_id, request, "insert", lambda engine, meta_table: insert_row(engine, meta_table, insert_in)
        )
        return RowOut(row=json_safe_dict(change.row))

    @router.delete("/{table_id}/rows/{pk}", status_code=204)
    def remove(table_id: int, pk: str, request: Request) -> None:
        """Удаляет строку."""
        apply_change(table_id, request, "delete", lambda engine, meta_table: delete_row(engine, meta_table, pk))

    return router
