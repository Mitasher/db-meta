import { useEffect, useState } from "react";
import { ApiError, executeSql, getSources, getSqlStatus } from "../api";
import { ConfirmDialog } from "../components/Dialog";
import { SimpleTable } from "../components/SimpleTable";
import { EmptyState, ErrorMessage, Loading } from "../components/StateView";
import type { SqlResult } from "../types";
import { errorText, useLoad } from "../utils/useLoad";

interface SqlConsolePageProps {
  onDataChanged: () => void;
}

interface PendingWrite {
  sql: string;
  sourceId: number;
  preview: SqlResult;
}

/** Экран «SQL-консоль»: SELECT выполняется сразу, изменения — после предпросмотра и подтверждения. */
export function SqlConsolePage({ onDataChanged }: SqlConsolePageProps) {
  const status = useLoad(getSqlStatus, []);
  const sources = useLoad(getSources, []);
  const [sourceId, setSourceId] = useState<number | null>(null);
  const [sql, setSql] = useState("");
  const [running, setRunning] = useState(false);
  const [result, setResult] = useState<SqlResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState<PendingWrite | null>(null);
  const [allRowsConfirmed, setAllRowsConfirmed] = useState(false);

  useEffect(() => {
    if (sourceId === null && sources.data && sources.data.length > 0) {
      setSourceId(sources.data[0].id);
    }
  }, [sourceId, sources.data]);

  const run = async () => {
    if (sourceId === null || !sql.trim()) {
      return;
    }
    setRunning(true);
    setError(null);
    setResult(null);
    try {
      const response = await executeSql({
        source_id: sourceId,
        sql,
        confirm: false,
        confirm_without_where: false,
        expected_rows: null,
      });
      if (response.status === "preview") {
        setAllRowsConfirmed(false);
        setPending({ sql, sourceId, preview: response });
      } else {
        setResult(response);
      }
    } catch (reason) {
      setError(errorText(reason));
    } finally {
      setRunning(false);
    }
  };

  const commit = async () => {
    if (!pending) {
      return;
    }
    setRunning(true);
    try {
      const response = await executeSql({
        source_id: pending.sourceId,
        sql: pending.sql,
        confirm: true,
        confirm_without_where: !pending.preview.has_where && allRowsConfirmed,
        expected_rows: pending.preview.affected_rows,
      });
      setResult(response);
      setError(null);
      // Запрос мог задеть любую таблицу — данные на других экранах надо перечитать
      onDataChanged();
    } catch (reason) {
      const conflict = reason instanceof ApiError && reason.status === 409;
      setError(conflict ? `${errorText(reason)}. Выполните запрос заново` : errorText(reason));
    } finally {
      setRunning(false);
      setPending(null);
    }
  };

  if (status.loading && !status.data) {
    return <Loading />;
  }
  if (status.error || !status.data) {
    return <ErrorMessage message={status.error ?? "Статус консоли не получен"} onRetry={status.reload} />;
  }
  if (!status.data.enabled) {
    return (
      <div className="page">
        <EmptyState text="SQL-консоль выключена на сервере (SQL_CONSOLE_ENABLED=false)" />
      </div>
    );
  }

  const affected = pending?.preview.affected_rows ?? 0;
  return (
    <div className="page">
      <header className="view-header">
        <div>
          <h1 className="view-title">SQL-консоль</h1>
          <div className="view-subtitle">
            Одна инструкция: SELECT, INSERT, UPDATE или DELETE · до {status.data.max_rows} строк · таймаут{" "}
            {status.data.timeout_ms / 1000} с
          </div>
        </div>
        {sources.data && sources.data.length > 1 && (
          <select
            className="input"
            value={sourceId ?? ""}
            onChange={(event) => setSourceId(Number(event.target.value))}
            aria-label="Источник"
          >
            {sources.data.map((source) => (
              <option key={source.id} value={source.id}>
                {source.name}
              </option>
            ))}
          </select>
        )}
      </header>
      {sources.error && <ErrorMessage message={sources.error} onRetry={sources.reload} />}

      <textarea
        className="input sql-editor"
        value={sql}
        spellCheck={false}
        placeholder="SELECT * FROM film WHERE id_film < 10"
        onChange={(event) => setSql(event.target.value)}
        onKeyDown={(event) => {
          if (event.key === "Enter" && (event.ctrlKey || event.metaKey)) {
            event.preventDefault();
            void run();
          }
        }}
        aria-label="SQL-запрос"
      />
      <div className="toolbar">
        <button type="button" className="button button-primary" onClick={run} disabled={running || !sql.trim() || sourceId === null}>
          {running ? "Выполняется…" : "Выполнить"}
        </button>
        <span className="muted">Ctrl+Enter</span>
      </div>

      {error && <ErrorMessage message={error} />}
      {result && result.statement_type === "SELECT" && (
        <div className="sql-result">
          <div className="muted">
            Строк: {result.rows.length}
            {result.truncated && ` — показаны первые ${status.data.max_rows}, остальные отброшены`}
          </div>
          {result.rows.length === 0 ? (
            <EmptyState text="Запрос ничего не вернул" />
          ) : (
            <SimpleTable columns={result.columns} rows={result.rows} />
          )}
        </div>
      )}
      {result && result.statement_type !== "SELECT" && (
        <div className="notice notice-success">
          {result.statement_type} выполнен, затронуто строк: {result.affected_rows ?? 0}
        </div>
      )}

      {pending && (
        <ConfirmDialog
          title={`Выполнить ${pending.preview.statement_type}?`}
          confirmText={`Изменить ${affected} строк`}
          danger
          busy={running}
          confirmDisabled={!pending.preview.has_where && !allRowsConfirmed}
          onConfirm={commit}
          onCancel={() => setPending(null)}
        >
          <p>
            Будет изменено строк: <strong>{affected}</strong>. Предпросмотр выполнен и откатан — пока ничего не
            записано.
          </p>
          <pre className="sql-preview">{pending.sql}</pre>
          {!pending.preview.has_where && (
            <label className="checkbox checkbox-danger">
              <input
                type="checkbox"
                checked={allRowsConfirmed}
                onChange={(event) => setAllRowsConfirmed(event.target.checked)}
              />
              В запросе нет WHERE — понимаю, что будут затронуты все строки таблицы
            </label>
          )}
        </ConfirmDialog>
      )}
    </div>
  );
}
