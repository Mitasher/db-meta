from typing import Any

from pydantic import BaseModel


class RowUpdateIn(BaseModel):
    """Правка строки: новые значения и исходные — чтобы проверить, что строку никто не поменял."""

    changes: dict[str, Any]
    original: dict[str, Any]


class RowInsertIn(BaseModel):
    """Новая строка."""

    values: dict[str, Any]


class RowOut(BaseModel):
    """Строка, как она лежит в БД после записи."""

    row: dict[str, Any]
