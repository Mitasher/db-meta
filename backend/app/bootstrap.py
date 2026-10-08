from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import Settings, load_settings
from app.crypto import encrypt_secret
from app.db import create_meta_engine
from app.models import DataSource


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
        )
    )
    session.commit()
    return True


def main() -> None:
    """Точка входа для python -m app.bootstrap."""
    settings = load_settings()
    engine = create_meta_engine(settings.meta_db_url)
    try:
        with Session(engine) as session:
            created = ensure_default_source(session, settings)
    finally:
        engine.dispose()
    if created:
        print(
            f"data_source: добавлен источник "
            f"{settings.source_db_host}:{settings.source_db_port}/{settings.source_db_name}"
        )
    else:
        print("data_source: источники уже есть, ничего не меняю")


if __name__ == "__main__":
    main()
