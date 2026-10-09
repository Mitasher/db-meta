import threading

from sqlalchemy import Engine

from app.db.models import DataSource
from app.services.source_connection import create_console_engine, create_source_engine


def connection_fingerprint(source: DataSource) -> tuple:
    """Параметры основного подключения: если любой поменялся, нужен новый движок."""
    return (
        source.db_type,
        source.host,
        source.port,
        source.database,
        source.username,
        source.password_encrypted,
    )


def console_fingerprint(source: DataSource) -> tuple:
    """Параметры подключения консоли."""
    return (
        source.db_type,
        source.host,
        source.port,
        source.database,
        source.console_username,
        source.console_password_encrypted,
    )


class SourceEngineCache:
    """Движки источников: основной и консольный на источник, пересоздаются при смене параметров."""

    def __init__(self, secret_key: str, console_timeout_ms: int) -> None:
        self._secret_key = secret_key
        self._console_timeout_ms = console_timeout_ms
        self._lock = threading.Lock()
        self._engines: dict[tuple[int, str], tuple[tuple, Engine]] = {}

    def get(self, source: DataSource) -> Engine:
        """Движок под основным пользователем; ValueError — если пароль не расшифровать."""
        return self._get(source, "data", connection_fingerprint(source))

    def get_console(self, source: DataSource) -> Engine:
        """Движок SQL-консоли; ValueError — если пользователь консоли не задан."""
        return self._get(source, "console", console_fingerprint(source))

    def _get(self, source: DataSource, role: str, fingerprint: tuple) -> Engine:
        """Движок из кэша или новый, если параметры подключения поменялись."""
        key = (source.id, role)
        # Обработчики FastAPI идут в пуле потоков — без блокировки два запроса создали бы два движка
        with self._lock:
            cached = self._engines.get(key)
            if cached is not None and cached[0] == fingerprint:
                return cached[1]
            if role == "console":
                engine = create_console_engine(source, self._secret_key, self._console_timeout_ms)
            else:
                engine = create_source_engine(source, self._secret_key)
            if cached is not None:
                cached[1].dispose()
            self._engines[key] = (fingerprint, engine)
            return engine

    def dispose_all(self) -> None:
        """Закрывает все соединения — при остановке приложения."""
        with self._lock:
            for _, engine in self._engines.values():
                engine.dispose()
            self._engines.clear()
