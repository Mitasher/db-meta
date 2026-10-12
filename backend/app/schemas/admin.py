from pydantic import BaseModel, ConfigDict, Field


class AdminTableOut(BaseModel):
    """Таблица в админке: все флаги, в том числе скрытые и исчезнувшие из источника."""

    id: int
    source_id: int
    schema_name: str
    name: str
    label: str | None
    is_visible: bool
    is_active: bool
    is_editable: bool
    allow_insert: bool
    allow_delete: bool
    # Почему строки не адресовать по ключу — тогда флаги редактирования ничего не дадут
    primary_key_problem: str | None


class AdminColumnOut(BaseModel):
    """Колонка в админке: настройки и то, что прочитала синхронизация."""

    id: int
    name: str
    label: str | None
    data_type: str
    type_group: str
    position: int
    is_visible: bool
    is_filterable: bool
    is_editable: bool
    is_primary_key: bool
    is_nullable: bool
    is_autoincrement: bool
    default_value: str | None
    is_active: bool


class AdminTableDetailOut(AdminTableOut):
    """Таблица со всеми колонками по порядку."""

    columns: list[AdminColumnOut]


class AdminColumnIn(BaseModel):
    """Настройки колонки, которые меняет человек."""

    model_config = ConfigDict(str_strip_whitespace=True)

    id: int
    label: str | None = Field(default=None, max_length=255)
    is_visible: bool
    is_filterable: bool
    is_editable: bool


class AdminTableIn(BaseModel):
    """Настройки таблицы и всех её колонок; порядок колонок в списке — порядок показа."""

    model_config = ConfigDict(str_strip_whitespace=True)

    label: str | None = Field(default=None, max_length=255)
    is_visible: bool
    is_editable: bool
    allow_insert: bool
    allow_delete: bool
    columns: list[AdminColumnIn]
