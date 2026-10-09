from typing import Any, Literal

from pydantic import BaseModel, Field


class SqlStatusOut(BaseModel):
    """Включена ли консоль и с какими ограничениями — фронт решает, показывать ли её."""

    enabled: bool
    max_rows: int
    timeout_ms: int


class SqlExecuteIn(BaseModel):
    """Запрос в консоль; для изменений — сначала без confirm (предпросмотр), потом с confirm."""

    source_id: int
    sql: str = Field(min_length=1, max_length=20000)
    confirm: bool = False
    confirm_without_where: bool = False
    expected_rows: int | None = None


class SqlResultOut(BaseModel):
    """Результат консоли: строки SELECT или число затронутых строк."""

    status: Literal["done", "preview"]
    statement_type: str
    columns: list[str] = Field(default_factory=list)
    # Списки, а не словари: в SELECT может быть две колонки с одним именем (a.id, b.id)
    rows: list[list[Any]] = Field(default_factory=list)
    truncated: bool = False
    affected_rows: int | None = None
    has_where: bool = True
