from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import Settings, load_settings
from app.core.crypto import encrypt_secret
from app.db.engine import create_meta_engine
from app.db.models import DataSource


def ensure_default_source(session: Session, settings: Settings) -> bool:
    """Заводит источник source-db, если источников ещё нет."""
    source_count = session.scalar(select(func.count()).select_from(DataSource))
    if source_count > 0:
        return False
    session.add(
        DataSource(
            name="Кастинг (source-db)",
            db_type="mysql",
            host=settings.source_db_host,
            port=settings.source_db_port,
            database=settings.source_db_name,
            username=settings.source_db_user,
            password_encrypted=encrypt_secret(settings.source_db_password, settings.secret_key),
            console_username=settings.source_db_console_user,
            console_password_encrypted=encrypt_secret(settings.source_db_console_password, settings.secret_key),
        )
    )
    session.commit()
    return True


def ensure_console_credentials(session: Session, settings: Settings) -> int | None:
    """Задаёт пользователя консоли источнику source-db, если его там ещё нет; возвращает id источника."""
    source = session.scalar(
        select(DataSource)
        .where(
            DataSource.host == settings.source_db_host,
            DataSource.port == settings.source_db_port,
            DataSource.database == settings.source_db_name,
            DataSource.console_username.is_(None),
        )
        .order_by(DataSource.id)
        .limit(1)
    )
    if source is None:
        return None
    source.console_username = settings.source_db_console_user
    source.console_password_encrypted = encrypt_secret(settings.source_db_console_password, settings.secret_key)
    session.commit()
    return source.id


def main() -> None:
    """Точка входа для python -m app.cli.bootstrap."""
    settings = load_settings()
    engine = create_meta_engine(settings.meta_db_url)
    try:
        with Session(engine) as session:
            created = ensure_default_source(session, settings)
            console_source_id = ensure_console_credentials(session, settings)
    finally:
        engine.dispose()
    if created:
        print(
            f"data_source: добавлен источник "
            f"{settings.source_db_host}:{settings.source_db_port}/{settings.source_db_name}"
        )
    else:
        print("data_source: источники уже есть, ничего не меняю")
    if console_source_id is not None:
        print(
            f"data_source: пользователю консоли источника {console_source_id} "
            f"задан {settings.source_db_console_user}"
        )
