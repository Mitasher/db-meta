from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.health import create_health_router
from app.api.sources import create_sources_router
from app.api.tables import create_tables_router
from app.core.config import load_settings
from app.db.engine import create_meta_engine
from app.services.engine_cache import SourceEngineCache


def create_app() -> FastAPI:
    """Собирает приложение."""
    settings = load_settings()
    meta_engine = create_meta_engine(settings.meta_db_url)
    engine_cache = SourceEngineCache(settings.secret_key)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        yield
        engine_cache.dispose_all()
        meta_engine.dispose()

    # Документация под /api — nginx проксирует на бэкенд только этот префикс
    app = FastAPI(
        title="bd_meta",
        lifespan=lifespan,
        docs_url="/api/docs",
        redoc_url=None,
        openapi_url="/api/openapi.json",
    )

    app.include_router(create_health_router(meta_engine, settings.secret_key))
    app.include_router(create_sources_router(meta_engine, settings.secret_key))
    app.include_router(create_tables_router(meta_engine, engine_cache))

    return app
