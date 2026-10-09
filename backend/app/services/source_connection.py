from sqlalchemy import URL, Engine, create_engine, event

from app.core.crypto import decrypt_secret
from app.db.engine import check_engine
from app.db.models import DataSource


def build_source_url(source: DataSource, username: str, password: str) -> URL:
    """URL подключения к источнику под заданным пользователем."""
    if source.db_type == "mysql":
        return URL.create(
            "mysql+pymysql",
            username=username,
            password=password,
            host=source.host,
            port=source.port,
            database=source.database,
            query={"charset": "utf8mb4"},
        )
    if source.db_type == "postgresql":
        return URL.create(
            "postgresql+psycopg",
            username=username,
            password=password,
            host=source.host,
            port=source.port,
            database=source.database,
        )
    raise ValueError(f"Неизвестный тип СУБД: {source.db_type}")


def create_source_engine(source: DataSource, secret_key: str) -> Engine:
    """Движок под основным пользователем источника; ValueError — если пароль не расшифровать."""
    password = decrypt_secret(source.password_encrypted, secret_key)
    return create_engine(build_source_url(source, source.username, password), pool_pre_ping=True)


def apply_session_limits(dbapi_connection, db_type: str, timeout_ms: int) -> None:
    """Ограничивает время запросов в новом соединении консоли."""
    cursor = dbapi_connection.cursor()
    try:
        if db_type == "mysql":
            # max_execution_time обрывает только SELECT; для UPDATE/DELETE ограничиваем ожидание блокировок, в секундах
            cursor.execute("SET SESSION max_execution_time = %s", (timeout_ms,))
            cursor.execute("SET SESSION innodb_lock_wait_timeout = %s", (max(1, timeout_ms // 1000),))
        elif db_type == "postgresql":
            cursor.execute("SELECT set_config('statement_timeout', %s, false)", (str(timeout_ms),))
    finally:
        cursor.close()
    # В PostgreSQL настройка внутри откатанной транзакции тоже откатится — фиксируем сразу
    dbapi_connection.commit()


def create_console_engine(source: DataSource, secret_key: str, timeout_ms: int) -> Engine:
    """Движок SQL-консоли: отдельный пользователь с урезанными правами и таймаут; ValueError — если его нет."""
    if source.console_username is None or source.console_password_encrypted is None:
        raise ValueError(f"У источника {source.name} не задан пользователь SQL-консоли")
    password = decrypt_secret(source.console_password_encrypted, secret_key)
    engine = create_engine(build_source_url(source, source.console_username, password), pool_pre_ping=True)
    db_type = source.db_type

    @event.listens_for(engine, "connect")
    def set_session_limits(dbapi_connection, connection_record) -> None:
        apply_session_limits(dbapi_connection, db_type, timeout_ms)

    return engine


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
