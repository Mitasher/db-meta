from logging.config import fileConfig

from alembic import context
from sqlalchemy import create_engine, pool

from app.config import read_env
from app.models import Base


def run_migrations_offline() -> None:
    """Генерирует SQL миграций без подключения к БД."""
    context.configure(
        url=read_env("META_DB_URL"),
        target_metadata=Base.metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Применяет миграции к meta-db."""
    engine = create_engine(read_env("META_DB_URL"), poolclass=pool.NullPool)
    try:
        with engine.connect() as connection:
            context.configure(connection=connection, target_metadata=Base.metadata)
            with context.begin_transaction():
                context.run_migrations()
    finally:
        engine.dispose()


def main() -> None:
    """Точка входа, которую вызывает Alembic."""
    if context.config.config_file_name is not None:
        fileConfig(context.config.config_file_name)
    if context.is_offline_mode():
        run_migrations_offline()
    else:
        run_migrations_online()


main()
