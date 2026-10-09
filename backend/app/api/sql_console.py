from fastapi import APIRouter, HTTPException, Request
from sqlalchemy import Engine
from sqlalchemy.orm import Session

from app.api.client import client_address
from app.db.models import DataSource
from app.schemas.sql_console import SqlExecuteIn, SqlResultOut, SqlStatusOut
from app.services.change_log import add_change
from app.services.engine_cache import SourceEngineCache
from app.services.sql_console import (
    SqlConfirmationError,
    SqlConflictError,
    SqlExecutionError,
    SqlRejectedError,
    classify_sql,
    run_sql,
)


def journal_action(result: SqlResultOut) -> str:
    """Тип записи журнала по результату консоли."""
    if result.statement_type == "SELECT":
        return "sql_select"
    if result.status == "preview":
        return "sql_preview"
    return "sql_write"


def create_sql_console_router(
    meta_engine: Engine,
    engine_cache: SourceEngineCache,
    enabled: bool,
    max_rows: int,
    timeout_ms: int,
) -> APIRouter:
    """SQL-консоль: отдельная страница фронта, отдельный пользователь БД, всё — через журнал."""
    router = APIRouter(prefix="/api/sql", tags=["sql"])

    @router.get("/status", response_model=SqlStatusOut)
    def status() -> SqlStatusOut:
        """Включена ли консоль и её ограничения."""
        return SqlStatusOut(enabled=enabled, max_rows=max_rows, timeout_ms=timeout_ms)

    @router.post("/execute", response_model=SqlResultOut)
    def execute(sql_in: SqlExecuteIn, request: Request) -> SqlResultOut:
        """Выполняет одну инструкцию; изменения — через предпросмотр и подтверждение."""
        if not enabled:
            raise HTTPException(status_code=403, detail="SQL-консоль отключена (SQL_CONSOLE_ENABLED=false)")
        with Session(meta_engine) as session:
            source = session.get(DataSource, sql_in.source_id)
            if source is None:
                raise HTTPException(status_code=404, detail=f"Источник {sql_in.source_id} не найден")
            address = client_address(request)

            def reject(status_code: int, error: Exception) -> HTTPException:
                """Пишет отказ в журнал и готовит ответ с ошибкой."""
                add_change(
                    session,
                    action="sql_rejected",
                    data_source_id=source.id,
                    sql_text=sql_in.sql,
                    message=str(error),
                    client_address=address,
                )
                return HTTPException(status_code=status_code, detail=str(error))

            try:
                classified = classify_sql(sql_in.sql, source.db_type)
            except SqlRejectedError as error:
                raise reject(400, error) from error
            try:
                engine = engine_cache.get_console(source)
            except ValueError as error:
                raise HTTPException(status_code=403, detail=str(error)) from error
            try:
                result = run_sql(engine, classified, sql_in, max_rows)
            except (SqlConfirmationError, SqlExecutionError) as error:
                raise reject(400, error) from error
            except SqlConflictError as error:
                raise reject(409, error) from error

            add_change(
                session,
                action=journal_action(result),
                data_source_id=source.id,
                sql_text=sql_in.sql,
                affected_rows=len(result.rows) if result.statement_type == "SELECT" else result.affected_rows,
                client_address=address,
            )
            return result

    return router
