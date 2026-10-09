from typing import Any

from pydantic import ValidationError
from sqlalchemy import Select, select
from sqlalchemy.orm import Session, joinedload, selectinload

from app.db.models import MetaTable, QueryTemplate
from app.schemas.tables import DataQueryIn
from app.schemas.templates import TemplateBodyV1, TemplateIn, TemplateOut
from app.services.table_data import QueryValidationError, build_page_statements
from app.services.table_meta import get_visible_table


class TemplateOutdatedError(Exception):
    """Шаблон больше не выполнить: таблицу или колонку скрыли, удалили, или тело не читается."""


def load_body(raw: dict[str, Any]) -> TemplateBodyV1:
    """Читает сохранённое тело шаблона с учётом его версии."""
    version = raw.get("schema_version")
    if version == 1:
        try:
            return TemplateBodyV1.model_validate(raw)
        except ValidationError as error:
            raise TemplateOutdatedError(f"Тело шаблона повреждено: {error}") from error
    # Новая версия формата — новая ветка здесь: прочитать старое тело и привести к актуальной модели
    raise TemplateOutdatedError(f"Неизвестная версия формата шаблона: {version!r}")


def body_to_query(body: TemplateBodyV1, page: int) -> DataQueryIn:
    """Запрос данных по телу шаблона."""
    return DataQueryIn(
        columns=body.columns,
        filters=body.filters,
        sort=body.sort,
        page=page,
        page_size=body.page_size,
    )


def template_statement() -> Select:
    """Выборка шаблонов вместе с таблицей, её колонками и источником."""
    return select(QueryTemplate).options(
        joinedload(QueryTemplate.meta_table).selectinload(MetaTable.meta_columns),
        joinedload(QueryTemplate.meta_table).joinedload(MetaTable.data_source),
    )


def list_templates(session: Session, table_id: int | None) -> list[QueryTemplate]:
    """Шаблоны по имени; можно сузить до одной таблицы."""
    statement = template_statement().order_by(QueryTemplate.name, QueryTemplate.id)
    if table_id is not None:
        statement = statement.where(QueryTemplate.meta_table_id == table_id)
    return list(session.scalars(statement).unique())


def get_template(session: Session, template_id: int) -> QueryTemplate | None:
    """Шаблон по id; None — если такого нет."""
    statement = template_statement().where(QueryTemplate.id == template_id)
    return session.scalars(statement).unique().one_or_none()


def prepare_query(template: QueryTemplate, page: int) -> DataQueryIn:
    """Проверяет, что шаблон ещё выполним по текущим метаданным, и собирает запрос данных."""
    meta_table = template.meta_table
    if not (meta_table.is_visible and meta_table.is_active):
        raise TemplateOutdatedError(
            f"Таблица {meta_table.table_name} скрыта или её больше нет в источнике"
        )
    query = body_to_query(load_body(template.body), page)
    try:
        build_page_statements(meta_table, query)
    except QueryValidationError as error:
        raise TemplateOutdatedError(f"Шаблон устарел: {error}") from error
    return query


def template_problems(template: QueryTemplate) -> list[str]:
    """Почему шаблон сейчас не выполнится; пустой список — всё в порядке."""
    try:
        prepare_query(template, page=1)
    except TemplateOutdatedError as error:
        return [str(error)]
    return []


def to_template_out(template: QueryTemplate) -> TemplateOut:
    """Шаблон для ответа API."""
    return TemplateOut(
        id=template.id,
        table_id=template.meta_table_id,
        name=template.name,
        description=template.description,
        body=template.body,
        created_at=template.created_at,
        updated_at=template.updated_at,
        problems=template_problems(template),
    )


def resolve_template_table(session: Session, template_in: TemplateIn) -> MetaTable:
    """Таблица шаблона; сам шаблон проверяется тем же кодом, что и запрос данных."""
    meta_table = get_visible_table(session, template_in.table_id)
    if meta_table is None:
        raise QueryValidationError(f"Таблица {template_in.table_id} не найдена или скрыта")
    build_page_statements(meta_table, body_to_query(template_in.body, page=1))
    return meta_table


def create_template(session: Session, template_in: TemplateIn) -> QueryTemplate:
    """Сохраняет новый шаблон; QueryValidationError — если он невалиден."""
    meta_table = resolve_template_table(session, template_in)
    template = QueryTemplate(
        meta_table_id=meta_table.id,
        name=template_in.name,
        description=template_in.description,
        body=template_in.body.model_dump(mode="json"),
    )
    session.add(template)
    session.commit()
    return get_template(session, template.id)


def update_template(session: Session, template: QueryTemplate, template_in: TemplateIn) -> QueryTemplate:
    """Заменяет шаблон целиком; QueryValidationError — если новый вариант невалиден."""
    meta_table = resolve_template_table(session, template_in)
    template.meta_table_id = meta_table.id
    template.name = template_in.name
    template.description = template_in.description
    template.body = template_in.body.model_dump(mode="json")
    session.commit()
    return get_template(session, template.id)


def delete_template(session: Session, template: QueryTemplate) -> None:
    """Удаляет шаблон."""
    session.delete(template)
    session.commit()
