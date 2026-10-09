from fastapi import APIRouter, HTTPException
from sqlalchemy import Engine
from sqlalchemy.orm import Session

from app.schemas.sources import SyncResultOut
from app.services.sync import SyncError, sync_source


def create_sources_router(meta_engine: Engine, secret_key: str) -> APIRouter:
    """Эндпоинты источников данных."""
    router = APIRouter(prefix="/api/sources", tags=["sources"])

    @router.post("/{source_id}/sync", response_model=SyncResultOut)
    def sync(source_id: int) -> SyncResultOut:
        """Синхронизирует метаданные источника."""
        with Session(meta_engine) as session:
            try:
                summary = sync_source(session, source_id, secret_key)
            except SyncError as error:
                # 502: упал не наш сервис, а источник за ним
                raise HTTPException(status_code=502, detail=str(error)) from error
            if summary is None:
                raise HTTPException(status_code=404, detail=f"Источник {source_id} не найден")
            return SyncResultOut.model_validate(summary)

    return router
