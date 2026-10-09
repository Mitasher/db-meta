from fastapi import APIRouter, HTTPException
from sqlalchemy import Engine
from sqlalchemy.orm import Session

from app.schemas.tables import DataPageOut
from app.schemas.templates import TemplateIn, TemplateOut, TemplateRunIn
from app.services.engine_cache import SourceEngineCache
from app.services.table_data import QueryValidationError, SourceQueryError, fetch_page
from app.services.templates import (
    TemplateOutdatedError,
    create_template,
    delete_template,
    get_template,
    list_templates,
    prepare_query,
    to_template_out,
    update_template,
)


def template_not_found(template_id: int) -> HTTPException:
    """Ответ для несуществующего шаблона."""
    return HTTPException(status_code=404, detail=f"Шаблон {template_id} не найден")


def create_templates_router(meta_engine: Engine, engine_cache: SourceEngineCache) -> APIRouter:
    """Эндпоинты шаблонов запросов."""
    router = APIRouter(prefix="/api/templates", tags=["templates"])

    @router.get("", response_model=list[TemplateOut])
    def list_all(table_id: int | None = None) -> list[TemplateOut]:
        """Все шаблоны или шаблоны одной таблицы."""
        with Session(meta_engine) as session:
            return [to_template_out(template) for template in list_templates(session, table_id)]

    @router.get("/{template_id}", response_model=TemplateOut)
    def get_one(template_id: int) -> TemplateOut:
        """Один шаблон."""
        with Session(meta_engine) as session:
            template = get_template(session, template_id)
            if template is None:
                raise template_not_found(template_id)
            return to_template_out(template)

    @router.post("", response_model=TemplateOut, status_code=201)
    def create(template_in: TemplateIn) -> TemplateOut:
        """Сохраняет новый шаблон, если он проходит проверку по метаданным."""
        with Session(meta_engine) as session:
            try:
                template = create_template(session, template_in)
            except QueryValidationError as error:
                raise HTTPException(status_code=400, detail=str(error)) from error
            return to_template_out(template)

    @router.put("/{template_id}", response_model=TemplateOut)
    def update(template_id: int, template_in: TemplateIn) -> TemplateOut:
        """Заменяет шаблон целиком."""
        with Session(meta_engine) as session:
            template = get_template(session, template_id)
            if template is None:
                raise template_not_found(template_id)
            try:
                template = update_template(session, template, template_in)
            except QueryValidationError as error:
                raise HTTPException(status_code=400, detail=str(error)) from error
            return to_template_out(template)

    @router.delete("/{template_id}", status_code=204)
    def delete(template_id: int) -> None:
        """Удаляет шаблон."""
        with Session(meta_engine) as session:
            template = get_template(session, template_id)
            if template is None:
                raise template_not_found(template_id)
            delete_template(session, template)

    @router.post("/{template_id}/run", response_model=DataPageOut)
    def run(template_id: int, run_in: TemplateRunIn | None = None) -> DataPageOut:
        """Выполняет шаблон; ответ — как у /api/tables/{id}/data."""
        page = run_in.page if run_in is not None else 1
        with Session(meta_engine) as session:
            template = get_template(session, template_id)
            if template is None:
                raise template_not_found(template_id)
            try:
                query = prepare_query(template, page)
            except TemplateOutdatedError as error:
                # 409: шаблон был правильным, но метаданные с тех пор поменялись
                raise HTTPException(status_code=409, detail=str(error)) from error
            try:
                engine = engine_cache.get(template.meta_table.data_source)
            except ValueError as error:
                raise HTTPException(status_code=502, detail=str(error)) from error
            try:
                return fetch_page(engine, template.meta_table, query)
            except QueryValidationError as error:
                raise HTTPException(status_code=409, detail=str(error)) from error
            except SourceQueryError as error:
                raise HTTPException(status_code=502, detail=str(error)) from error

    return router
