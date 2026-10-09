import threading

from sqlalchemy import Engine

from app.db.models import DataSource
from app.services.source_connection import create_source_engine


def connection_fingerprint(source: DataSource) -> tuple:
    """Параметры подключения: если любой поменялся, нужен новый движок."""
    return (
        source.db_type,
        source.host,
        source.port,
        source.database,
        source.username,
        source.password_encrypted,
    )


class SourceEngineCache:
    """Движки источников: один на источник, пересоздаётся при смене параметров подключения."""

    def __init__(self, secret_key: str) -> None:
        self._secret_key = secret_key
        self._lock = threading.Lock()
        self._engines: dict[int, tuple[tuple, Engine]] = {}

    def get(self, source: DataSource) -> Engine:
        """Движок для источника; ValueError — если пароль не расшифровать."""
        fingerprint = connection_fingerprint(source)
        # Обработчики FastAPI идут в пуле потоков — без блокировки два запроса создали бы два движка
        with self._lock:
            cached = self._engines.get(source.id)
            if cached is not None and cached[0] == fingerprint:
                return cached[1]
            engine = create_source_engine(source, self._secret_key)
            if cached is not None:
                cached[1].dispose()
            self._engines[source.id] = (fingerprint, engine)
            return engine

    def dispose_all(self) -> None:
        """Закрывает все соединения — при остановке приложения."""
        with self._lock:
            for _, engine in self._engines.values():
                engine.dispose()
            self._engines.clear()
