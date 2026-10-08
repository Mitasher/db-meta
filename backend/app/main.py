import os

from fastapi import FastAPI
from sqlalchemy import create_engine, text


def read_env(name: str) -> str:
    """Читает обязательную переменную окружения."""
    value = os.environ.get(name)
    if value is None or value == "":
        raise RuntimeError(f"Не задана переменная окружения {name}")
    return value


def check_database(url: str) -> str:
    """Проверяет, что БД отвечает."""
    engine = create_engine(url)
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return "ok"
    except Exception as error:
        return f"error: {error.__class__.__name__}: {error}"
    finally:
        engine.dispose()


def create_app() -> FastAPI:
    """Собирает приложение."""
    app = FastAPI(title="bd_meta")

    @app.get("/api/health")
    def health() -> dict:
        return {
            "meta_db": check_database(read_env("META_DB_URL")),
            "source_db": check_database(read_env("SOURCE_DB_URL")),
        }

    return app