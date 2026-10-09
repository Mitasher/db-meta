from fastapi import APIRouter, Query
from sqlalchemy import Engine
from sqlalchemy.orm import Session

from app.schemas.change_log import ChangeLogOut
from app.services.change_log import list_changes


def create_change_log_router(meta_engine: Engine) -> APIRouter:
    """Чтение журнала изменений."""
    router = APIRouter(prefix="/api/change-log", tags=["change-log"])

    @router.get("", response_model=list[ChangeLogOut])
    def changes(
        table_id: int | None = None,
        source_id: int | None = None,
        limit: int = Query(default=50, ge=1, le=200),
        before_id: int | None = None,
    ) -> list[ChangeLogOut]:
        """Записи от новых к старым; следующая порция — before_id = id последней полученной."""
        with Session(meta_engine) as session:
            return [
                ChangeLogOut.model_validate(entry)
                for entry in list_changes(session, table_id, source_id, limit, before_id)
            ]

    return router
