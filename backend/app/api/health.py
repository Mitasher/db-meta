from fastapi import APIRouter
from sqlalchemy import Engine, select
from sqlalchemy.orm import Session

from app.db.engine import check_engine
from app.db.models import DataSource
from app.schemas.health import HealthOut, SourceStatusOut
from app.services.source_connection import check_source


def create_health_router(meta_engine: Engine, secret_key: str) -> APIRouter:
    """Проверка, что бэкенд и его БД живы."""
    router = APIRouter(prefix="/api", tags=["health"])

    @router.get("/health", response_model=HealthOut)
    def health() -> HealthOut:
        """Отвечает ли meta-db и каждый источник."""
        meta_status = check_engine(meta_engine)
        sources = []
        if meta_status == "ok":
            with Session(meta_engine) as session:
                for source in session.scalars(select(DataSource).order_by(DataSource.id)):
                    sources.append(
                        SourceStatusOut(
                            id=source.id,
                            name=source.name,
                            status=check_source(source, secret_key),
                        )
                    )
        return HealthOut(meta_db=meta_status, sources=sources)

    return router
