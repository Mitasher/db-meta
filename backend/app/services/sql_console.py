from dataclasses import dataclass

import sqlglot
from sqlglot import exp
from sqlglot.errors import SqlglotError
from sqlalchemy import Engine
from sqlalchemy.engine import Connection, CursorResult
from sqlalchemy.exc import SQLAlchemyError

from app.schemas.sql_console import SqlExecuteIn, SqlResultOut
from app.services.change_log import json_safe


class SqlRejectedError(Exception):
    """Запрос не пропущен: не разобрался, несколько инструкций или запрещённый тип."""


class SqlConfirmationError(Exception):
    """Для коммита не хватает подтверждения."""


class SqlConflictError(Exception):
    """Число затронутых строк не совпало с предпросмотром."""


class SqlExecutionError(Exception):
    """Источник вернул ошибку при выполнении: синтаксис, нет прав, таймаут."""


@dataclass(frozen=True)
class ClassifiedSql:
    """Что за запрос пришёл в консоль."""

    statement_type: str
    is_read: bool
    has_where: bool


def sqlglot_dialect(db_type: str) -> str:
    """Имя диалекта sqlglot для типа СУБД источника."""
    if db_type == "mysql":
        return "mysql"
    if db_type == "postgresql":
        return "postgres"
    raise SqlRejectedError(f"SQL-консоль не поддерживает СУБД {db_type}")


def classify_sql(sql: str, db_type: str) -> ClassifiedSql:
    """Разбирает запрос парсером и пропускает только одну инструкцию SELECT/INSERT/UPDATE/DELETE."""
    try:
        statements = [statement for statement in sqlglot.parse(sql, read=sqlglot_dialect(db_type)) if statement is not None]
    except SqlglotError as error:
        raise SqlRejectedError(f"Не удалось разобрать запрос: {error}") from error
    if not statements:
        raise SqlRejectedError("Пустой запрос")
    # Несколько инструкций — классический путь для «SELECT 1; DROP TABLE ...»
    if len(statements) > 1:
        raise SqlRejectedError("За раз можно выполнить только одну инструкцию")
    statement = statements[0]

    # Белый список: всё, что не перечислено, запрещено — DROP, TRUNCATE, ALTER, GRANT, SET, CALL и т. д.
    if isinstance(statement, (exp.Select, exp.Union, exp.Intersect, exp.Except)):
        if statement.find(exp.Insert, exp.Update, exp.Delete) is not None:
            raise SqlRejectedError("Внутри SELECT не может быть изменяющего подзапроса")
        return ClassifiedSql(statement_type="SELECT", is_read=True, has_where=True)
    if isinstance(statement, exp.Insert):
        return ClassifiedSql(statement_type="INSERT", is_read=False, has_where=True)
    if isinstance(statement, (exp.Update, exp.Delete)):
        return ClassifiedSql(
            statement_type=statement.key.upper(),
            is_read=False,
            has_where=statement.args.get("where") is not None,
        )
    raise SqlRejectedError(
        f"Запрещённый тип запроса: {statement.key.upper()}. Разрешены только SELECT, INSERT, UPDATE и DELETE"
    )


def execute_raw(connection: Connection, sql: str) -> CursorResult:
    """Выполняет SQL пользователя как есть."""
    # no_parameters: иначе драйвер примет % в LIKE '%а%' за место для параметра
    return connection.exec_driver_sql(sql, execution_options={"no_parameters": True})


def read_rows(connection: Connection, sql: str, max_rows: int) -> SqlResultOut:
    """SELECT: не больше max_rows строк и признак, что результат обрезан."""
    result = execute_raw(connection, sql)
    columns = list(result.keys())
    # На одну строку больше лимита — чтобы понять, есть ли что-то сверх него
    fetched = result.fetchmany(max_rows + 1)
    result.close()
    return SqlResultOut(
        status="done",
        statement_type="SELECT",
        columns=columns,
        rows=[[json_safe(value) for value in row] for row in fetched[:max_rows]],
        truncated=len(fetched) > max_rows,
    )


def check_confirmation(classified: ClassifiedSql, sql_in: SqlExecuteIn, affected_rows: int) -> None:
    """Коммит — только с подтверждением; без WHERE — отдельным флагом; число строк — как в предпросмотре."""
    if not classified.has_where and not sql_in.confirm_without_where:
        raise SqlConfirmationError(
            f"{classified.statement_type} без WHERE затронет все строки таблицы — нужно отдельное подтверждение "
            f"confirm_without_where"
        )
    if sql_in.expected_rows is None:
        raise SqlConfirmationError("Нужно число строк из предпросмотра: expected_rows")
    if sql_in.expected_rows != affected_rows:
        raise SqlConflictError(
            f"В предпросмотре было {sql_in.expected_rows} строк, сейчас {affected_rows} — "
            f"данные изменились, сделайте предпросмотр заново"
        )


def write_rows(connection: Connection, sql: str, classified: ClassifiedSql, sql_in: SqlExecuteIn) -> SqlResultOut:
    """INSERT/UPDATE/DELETE: без confirm — выполнить, посчитать строки и откатить; с confirm — проверить и зафиксировать."""
    transaction = connection.begin()
    try:
        affected_rows = execute_raw(connection, sql).rowcount
        if not sql_in.confirm:
            transaction.rollback()
            return SqlResultOut(
                status="preview",
                statement_type=classified.statement_type,
                affected_rows=affected_rows,
                has_where=classified.has_where,
            )
        check_confirmation(classified, sql_in, affected_rows)
        transaction.commit()
    except BaseException:
        transaction.rollback()
        raise
    return SqlResultOut(
        status="done",
        statement_type=classified.statement_type,
        affected_rows=affected_rows,
        has_where=classified.has_where,
    )


def run_sql(engine: Engine, classified: ClassifiedSql, sql_in: SqlExecuteIn, max_rows: int) -> SqlResultOut:
    """Выполняет запрос консоли; ошибки источника превращает в SqlExecutionError."""
    try:
        with engine.connect() as connection:
            if classified.is_read:
                return read_rows(connection, sql_in.sql, max_rows)
            return write_rows(connection, sql_in.sql, classified, sql_in)
    except SQLAlchemyError as error:
        reason = error.orig if getattr(error, "orig", None) is not None else error
        raise SqlExecutionError(f"Ошибка выполнения: {reason}") from error
