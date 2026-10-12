from fastapi import APIRouter, HTTPException
from sqlalchemy import Engine
from sqlalchemy.orm import Session

from app.api.tables import table_not_found
from app.schemas.admin import AdminTableDetailOut, AdminTableIn, AdminTableOut
from app.services.admin import (
    AdminValidationError,
    get_any_table,
    list_all_tables,
    to_admin_table_detail_out,
    to_admin_table_out,
    update_table_settings,
)


def create_admin_router(meta_engine: Engine) -> APIRouter:
    """Настройка метаданных: подписи, видимость, порядок и флаги редактирования."""
    router = APIRouter(prefix="/api/admin/tables", tags=["admin"])

    @router.get("", response_model=list[AdminTableOut])
    def tables(source_id: int | None = None) -> list[AdminTableOut]:
        """Все таблицы, включая скрытые и исчезнувшие из источника."""
        with Session(meta_engine) as session:
            return [to_admin_table_out(meta_table) for meta_table in list_all_tables(session, source_id)]

    @router.get("/{table_id}", response_model=AdminTableDetailOut)
    def table(table_id: int) -> AdminTableDetailOut:
        """Таблица со всеми колонками."""
        with Session(meta_engine) as session:
            meta_table = get_any_table(session, table_id)
            if meta_table is None:
                raise table_not_found(table_id)
            return to_admin_table_detail_out(meta_table)

    @router.put("/{table_id}", response_model=AdminTableDetailOut)
    def update(table_id: int, table_in: AdminTableIn) -> AdminTableDetailOut:
        """Сохраняет настройки таблицы и всех её колонок разом."""
        with Session(meta_engine) as session:
            meta_table = get_any_table(session, table_id)
            if meta_table is None:
                raise table_not_found(table_id)
            try:
                meta_table = update_table_settings(session, meta_table, table_in)
            except AdminValidationError as error:
                raise HTTPException(status_code=400, detail=str(error)) from error
            return to_admin_table_detail_out(meta_table)

    return router
