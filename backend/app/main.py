from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.change_log import create_change_log_router
from app.api.health import create_health_router
from app.api.rows import create_rows_router
from app.api.sources import create_sources_router
from app.api.sql_console import create_sql_console_router
from app.api.tables import create_tables_router
from app.api.templates import create_templates_router
from app.core.config import load_settings
from app.db.engine import create_meta_engine
from app.services.engine_cache import SourceEngineCache


def create_app() -> FastAPI:
    """Собирает приложение."""
    settings = load_settings()
    meta_engine = create_meta_engine(settings.meta_db_url)
    engine_cache = SourceEngineCache(settings.secret_key, settings.sql_console_timeout_ms)

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
    app.include_router(create_rows_router(meta_engine, engine_cache))
    app.include_router(create_templates_router(meta_engine, engine_cache))
    app.include_router(create_change_log_router(meta_engine))
    app.include_router(
        create_sql_console_router(
            meta_engine,
            engine_cache,
            enabled=settings.sql_console_enabled,
            max_rows=settings.sql_console_max_rows,
            timeout_ms=settings.sql_console_timeout_ms,
        )
    )

    return app
