from sqlalchemy import URL, Engine, create_engine

from app.core.crypto import decrypt_secret
from app.db.engine import check_engine
from app.db.models import DataSource


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


def create_source_engine(source: DataSource, secret_key: str) -> Engine:
    """Движок для источника; ValueError — если пароль не расшифровать или тип СУБД неизвестен."""
    url = build_source_url(source, decrypt_secret(source.password_encrypted, secret_key))
    return create_engine(url, pool_pre_ping=True)


def check_source(source: DataSource, secret_key: str) -> str:
    """Проверяет подключение к источнику."""
    try:
        engine = create_source_engine(source, secret_key)
    except ValueError as error:
        return f"error: {error}"
    try:
        return check_engine(engine)
    finally:
        engine.dispose()
