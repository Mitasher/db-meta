from sqlalchemy import URL, create_engine

from app.crypto import decrypt_secret
from app.db import check_engine
from app.models import DataSource


def build_source_url(source: DataSource, password: str) -> URL:
    """URL подключения к источнику по записи data_source."""
    if source.db_type == "mysql":
        return URL.create(
            "mysql+pymysql",
            username=source.username,
            password=password,
            host=source.host,
            port=source.port,
            database=source.database,
            query={"charset": "utf8mb4"},
        )
    if source.db_type == "postgresql":
        return URL.create(
            "postgresql+psycopg",
            username=source.username,
            password=password,
            host=source.host,
            port=source.port,
            database=source.database,
        )
    raise ValueError(f"Неизвестный тип СУБД: {source.db_type}")


def check_source(source: DataSource, secret_key: str) -> str:
    """Проверяет подключение к источнику."""
    try:
        url = build_source_url(source, decrypt_secret(source.password_encrypted, secret_key))
    except ValueError as error:
        return f"error: {error}"
    engine = create_engine(url)
    try:
        return check_engine(engine)
    finally:
        engine.dispose()
