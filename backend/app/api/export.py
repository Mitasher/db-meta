from datetime import datetime
from urllib.parse import quote

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy import Engine
from sqlalchemy.orm import Session

from app.api.tables import table_not_found
from app.api.templates import template_not_found
from app.schemas.export import ExportIn
from app.services.engine_cache import SourceEngineCache
from app.services.export import XLSX_MEDIA_TYPE, ExportTooLargeError, export_filename, iter_file, write_xlsx
from app.services.table_data import QueryValidationError, SourceQueryError
from app.services.table_meta import get_visible_table
from app.services.templates import TemplateOutdatedError, get_template, prepare_query


def content_disposition(filename: str) -> str:
    """Заголовок скачивания: ASCII-имя для старых клиентов и полное UTF-8 имя для остальных."""
    ascii_name = "".join(char if char.isascii() and char not in '"\\' else "_" for char in filename)
    return f"attachment; filename=\"{ascii_name}\"; filename*=UTF-8''{quote(filename)}"


def create_export_router(meta_engine: Engine, engine_cache: SourceEngineCache, max_rows: int) -> APIRouter:
    """Выгрузка данных в Excel."""
    router = APIRouter(prefix="/api/export", tags=["export"])

    @router.post("", response_class=StreamingResponse)
    def export(export_in: ExportIn) -> StreamingResponse:
        """Все строки по фильтрам таблицы или шаблона в xlsx; подписи колонок — из метаданных."""
        with Session(meta_engine) as session:
            if export_in.template_id is not None:
                template = get_template(session, export_in.template_id)
                if template is None:
                    raise template_not_found(export_in.template_id)
                try:
                    query = prepare_query(template, page=1)
                except TemplateOutdatedError as error:
                    raise HTTPException(status_code=409, detail=str(error)) from error
                meta_table = template.meta_table
            else:
                meta_table = get_visible_table(session, export_in.table_id)
                if meta_table is None:
                    raise table_not_found(export_in.table_id)
                query = export_in.query
            try:
                engine = engine_cache.get(meta_table.data_source)
            except ValueError as error:
                raise HTTPException(status_code=502, detail=str(error)) from error
            try:
                output = write_xlsx(engine, meta_table, query, max_rows)
            except (QueryValidationError, ExportTooLargeError) as error:
                raise HTTPException(status_code=400, detail=str(error)) from error
            except SourceQueryError as error:
                raise HTTPException(status_code=502, detail=str(error)) from error
            filename = export_filename(meta_table, datetime.now())

        return StreamingResponse(
            iter_file(output),
            media_type=XLSX_MEDIA_TYPE,
            headers={"Content-Disposition": content_disposition(filename)},
        )

    return router
