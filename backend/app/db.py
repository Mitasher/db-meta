from sqlalchemy import Engine, create_engine, text


def create_meta_engine(meta_db_url: str) -> Engine:
    """Движок для meta-db."""
    return create_engine(meta_db_url, pool_pre_ping=True)


def check_engine(engine: Engine) -> str:
    """Проверяет, что БД отвечает."""
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return "ok"
    except Exception as error:
        return f"error: {error.__class__.__name__}: {error}"
