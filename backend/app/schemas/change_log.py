from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class ChangeLogOut(BaseModel):
    """Запись журнала изменений."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    data_source_id: int | None
    meta_table_id: int | None
    action: str
    row_key: dict[str, Any] | None
    old_values: dict[str, Any] | None
    new_values: dict[str, Any] | None
    sql_text: str | None
    affected_rows: int | None
    message: str | None
    client_address: str | None
