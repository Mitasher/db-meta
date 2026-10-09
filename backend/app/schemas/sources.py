from datetime import datetime

from pydantic import BaseModel, ConfigDict


class SyncCounterOut(BaseModel):
    """Счётчики одного вида объектов."""

    model_config = ConfigDict(from_attributes=True)

    added: int
    updated: int
    deactivated: int


class SyncResultOut(BaseModel):
    """Ответ на синхронизацию источника."""

    model_config = ConfigDict(from_attributes=True)

    source_id: int
    schema_name: str
    synced_at: datetime
    tables: SyncCounterOut
    columns: SyncCounterOut
