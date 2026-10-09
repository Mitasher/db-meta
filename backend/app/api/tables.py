from fastapi import APIRouter, HTTPException
from sqlalchemy import Engine
from sqlalchemy.orm import Session

from app.schemas.tables import DataPageOut, DataQueryIn, TableMetaOut, TableOut
from app.services.engine_cache import SourceEngineCache
from app.services.table_data import QueryValidationError, SourceQueryError, fetch_page
from app.services.table_meta import (
    get_visible_table,
    list_visible_tables,
    to_table_meta_out,
    to_table_out,
)


def table_not_found(table_id: int) -> HTTPException:
    """Ответ для скрытой, неактивной или несуществующей таблицы."""
    return HTTPException(status_code=404, detail=f"Таблица {table_id} не найдена")


def create_tables_router(meta_engine: Engine, engine_cache: SourceEngineCache) -> APIRouter:
    """Эндпоинты чтения таблиц источника."""
    router = APIRouter(prefix="/api/tables", tags=["tables"])

    @router.get("", response_model=list[TableOut])
    def tables(source_id: int | None = None) -> list[TableOut]:
        """Видимые таблицы с подписями."""
        with Session(meta_engine) as session:
            return [to_table_out(meta_table) for meta_table in list_visible_tables(session, source_id)]

    @router.get("/{table_id}/meta", response_model=TableMetaOut)
    def table_meta(table_id: int) -> TableMetaOut:
        """Видимые колонки таблицы с типами, флагами и операторами."""
        with Session(meta_engine) as session:
            meta_table = get_visible_table(session, table_id)
            if meta_table is None:
                raise table_not_found(table_id)
            return to_table_meta_out(meta_table)

    @router.post("/{table_id}/data", response_model=DataPageOut)
    def table_data(table_id: int, query: DataQueryIn) -> DataPageOut:
        """Страница данных с фильтрами и сортировкой."""
        with Session(meta_engine) as session:
            meta_table = get_visible_table(session, table_id)
            if meta_table is None:
                raise table_not_found(table_id)
            try:
                engine = engine_cache.get(meta_table.data_source)
            except ValueError as error:
                raise HTTPException(status_code=502, detail=str(error)) from error
            try:
                return fetch_page(engine, meta_table, query)
            except QueryValidationError as error:
                raise HTTPException(status_code=400, detail=str(error)) from error
            except SourceQueryError as error:
                # 502: упал не наш сервис, а источник за ним
                raise HTTPException(status_code=502, detail=str(error)) from error

    return router
