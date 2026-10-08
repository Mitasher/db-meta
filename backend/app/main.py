from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import load_settings
from app.db import check_engine, create_meta_engine
from app.models import DataSource
from app.sources import check_source


def create_app() -> FastAPI:
    """Собирает приложение."""
    settings = load_settings()
    meta_engine = create_meta_engine(settings.meta_db_url)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        yield
        meta_engine.dispose()

    app = FastAPI(title="bd_meta", lifespan=lifespan)

    @app.get("/api/health")
    def health() -> dict:
        meta_status = check_engine(meta_engine)
        sources = []
        if meta_status == "ok":
            with Session(meta_engine) as session:
                for source in session.scalars(select(DataSource).order_by(DataSource.id)):
                    sources.append(
                        {
                            "id": source.id,
                            "name": source.name,
                            "status": check_source(source, settings.secret_key),
                        }
                    )
        return {"meta_db": meta_status, "sources": sources}

    return app
