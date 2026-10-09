from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.tables import FilterIn, SortIn


class TemplateBodyV1(BaseModel):
    """Тело шаблона, версия 1: какие колонки, фильтры, сортировка и размер страницы."""

    # Лишнее поле — ошибка: опечатка вроде "filter" иначе молча потеряется
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal[1] = 1
    columns: list[str] | None = None
    filters: list[FilterIn] = Field(default_factory=list, max_length=50)
    sort: list[SortIn] = Field(default_factory=list, max_length=10)
    # Тот же потолок, что у запроса данных
    page_size: int = Field(default=50, ge=1, le=500)


class TemplateIn(BaseModel):
    """Создание и изменение шаблона."""

    model_config = ConfigDict(str_strip_whitespace=True)

    table_id: int
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None
    body: TemplateBodyV1


class TemplateOut(BaseModel):
    """Шаблон; problems не пустой, если шаблон устарел и не выполнится."""

    id: int
    table_id: int
    name: str
    description: str | None
    body: dict[str, Any]
    created_at: datetime
    updated_at: datetime
    problems: list[str]


class TemplateRunIn(BaseModel):
    """Какую страницу результата шаблона вернуть."""

    page: int = Field(default=1, ge=1)
