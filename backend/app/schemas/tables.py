from typing import Any, Literal

from pydantic import BaseModel, Field


class TableOut(BaseModel):
    """Таблица в списке."""

    id: int
    source_id: int
    schema_name: str
    name: str
    label: str


class ColumnOut(BaseModel):
    """Колонка: по этим полям фронт рисует таблицу и форму фильтров."""

    id: int
    name: str
    label: str
    data_type: str
    type_group: str
    is_primary_key: bool
    is_filterable: bool
    operators: list[str]


class TableMetaOut(TableOut):
    """Таблица вместе с видимыми колонками."""

    columns: list[ColumnOut]


class FilterIn(BaseModel):
    """Условие фильтра; несколько условий объединяются через AND."""

    column: str
    operator: Literal["eq", "ne", "gt", "lt", "between", "like", "in", "is_null", "is_not_null"]
    value: Any = None


class SortIn(BaseModel):
    """Сортировка по одной колонке."""

    column: str
    direction: Literal["asc", "desc"] = "asc"


class DataQueryIn(BaseModel):
    """Запрос страницы данных."""

    columns: list[str] | None = None
    filters: list[FilterIn] = Field(default_factory=list, max_length=50)
    sort: list[SortIn] = Field(default_factory=list, max_length=10)
    page: int = Field(default=1, ge=1)
    # Потолок из плана: больше 500 строк за раз не отдаём
    page_size: int = Field(default=50, ge=1, le=500)


class DataPageOut(BaseModel):
    """Страница данных."""

    columns: list[str]
    rows: list[dict[str, Any]]
    total: int
    page: int
    page_size: int
