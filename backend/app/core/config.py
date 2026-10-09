import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    """Настройки из переменных окружения."""

    meta_db_url: str
    secret_key: str
    source_db_host: str
    source_db_port: int
    source_db_name: str
    source_db_user: str
    source_db_password: str


def read_env(name: str) -> str:
    """Читает обязательную переменную окружения."""
    value = os.environ.get(name)
    if value is None or value == "":
        raise RuntimeError(f"Не задана переменная окружения {name}")
    return value


def read_env_int(name: str) -> int:
    """Читает обязательную числовую переменную окружения."""
    value = read_env(name)
    if not value.isdigit():
        raise RuntimeError(f"Переменная окружения {name} должна быть числом, а сейчас: {value}")
    return int(value)


def load_settings() -> Settings:
    """Собирает настройки"""
    return Settings(
        meta_db_url=read_env("META_DB_URL"),
        secret_key=read_env("META_SECRET_KEY"),
        source_db_host=read_env("SOURCE_DB_HOST"),
        source_db_port=read_env_int("SOURCE_DB_PORT"),
        source_db_name=read_env("SOURCE_DB_NAME"),
        source_db_user=read_env("SOURCE_DB_USER"),
        source_db_password=read_env("SOURCE_DB_PASSWORD"),
    )
