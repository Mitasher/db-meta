import { useEffect, useState } from "react";
import { getAdminTables, getChangeLog } from "../api";
import { EmptyState, ErrorMessage, Loading } from "../components/StateView";
import type { ChangeAction, ChangeLogEntry, Row } from "../types";
import { errorText, useLoad } from "../utils/useLoad";

// Сколько записей загружать за раз
const PAGE_LIMIT = 50;

const ACTION_LABELS: Record<ChangeAction, string> = {
  update: "изменение",
  insert: "добавление",
  delete: "удаление",
  sql_select: "SQL: чтение",
  sql_preview: "SQL: предпросмотр",
  sql_write: "SQL: изменение",
  sql_rejected: "SQL: отклонён",
};

/** Значение из журнала для показа. */
function show(value: unknown): string {
  if (value === null || value === undefined) {
    return "NULL";
  }
  return String(value);
}

/** Ключ строки: id=5. */
function describeKey(key: Row | null): string {
  if (!key) {
    return "";
  }
  return Object.entries(key)
    .map(([name, value]) => `${name}=${show(value)}`)
    .join(", ");
}

/** Что поменялось: поле — было → стало. */
function Changes({ entry }: { entry: ChangeLogEntry }) {
  const names = Array.from(new Set([...Object.keys(entry.old_values ?? {}), ...Object.keys(entry.new_values ?? {})]));
  if (names.length === 0) {
    return null;
  }
  return (
    <ul className="change-list">
      {names.map((name) => (
        <li key={name}>
          <code>{name}</code>:{" "}
          {entry.old_values && <span className="change-old">{show(entry.old_values[name])}</span>}
          {entry.old_values && entry.new_values && " → "}
          {entry.new_values && <span className="change-new">{show(entry.new_values[name])}</span>}
        </li>
      ))}
    </ul>
  );
}

/** Экран «История изменений»: журнал правок и запросов консоли. */
export function HistoryPage() {
  const tables = useLoad(getAdminTables, []);
  const [tableId, setTableId] = useState<number | null>(null);
  const [entries, setEntries] = useState<ChangeLogEntry[]>([]);
  const [hasMore, setHasMore] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [attempt, setAttempt] = useState(0);
  const tableLabels = new Map((tables.data ?? []).map((table) => [table.id, table.label || table.name]));

  const load = async (beforeId: number | undefined, append: boolean) => {
    setLoading(true);
    setError(null);
    try {
      const portion = await getChangeLog({
        table_id: tableId ?? undefined,
        limit: PAGE_LIMIT,
        before_id: beforeId,
      });
      setEntries((current) => (append ? [...current, ...portion] : portion));
      setHasMore(portion.length === PAGE_LIMIT);
    } catch (reason) {
      setError(errorText(reason));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void load(undefined, false);
    // Перезагрузка — только при смене фильтра или по кнопке
  }, [tableId, attempt]);

  return (
    <div className="page">
      <header className="view-header">
        <div>
          <h1 className="view-title">История изменений</h1>
          <div className="view-subtitle">Правки строк и запросы SQL-консоли, новые сверху</div>
        </div>
        <div className="toolbar">
          <select
            className="input"
            value={tableId ?? ""}
            onChange={(event) => setTableId(event.target.value ? Number(event.target.value) : null)}
            aria-label="Таблица"
          >
            <option value="">Все таблицы и консоль</option>
            {(tables.data ?? []).map((table) => (
              <option key={table.id} value={table.id}>
                {table.label || table.name}
              </option>
            ))}
          </select>
          <button type="button" className="button button-small" onClick={() => setAttempt((value) => value + 1)} disabled={loading}>
            Обновить
          </button>
        </div>
      </header>

      {error && <ErrorMessage message={error} onRetry={() => setAttempt((value) => value + 1)} />}
      {!loading && !error && entries.length === 0 && <EmptyState text="Журнал пуст" />}
      {entries.length > 0 && (
        <div className="table-wrap">
          <table className="data-table history-table">
            <thead>
              <tr>
                <th>Когда</th>
                <th>Действие</th>
                <th>Где</th>
                <th>Что</th>
                <th>Клиент</th>
              </tr>
            </thead>
            <tbody>
              {entries.map((entry) => (
                <tr key={entry.id}>
                  <td className="nowrap">{new Date(entry.created_at).toLocaleString("ru-RU")}</td>
                  <td>
                    <span className={`badge badge-action-${entry.action}`}>{ACTION_LABELS[entry.action] ?? entry.action}</span>
                  </td>
                  <td>
                    {entry.meta_table_id !== null && (
                      <div>{tableLabels.get(entry.meta_table_id) ?? `таблица #${entry.meta_table_id}`}</div>
                    )}
                    {entry.row_key && <div className="muted">{describeKey(entry.row_key)}</div>}
                  </td>
                  <td>
                    <Changes entry={entry} />
                    {entry.sql_text && <pre className="sql-preview">{entry.sql_text}</pre>}
                    {entry.affected_rows !== null && <div className="muted">строк: {entry.affected_rows}</div>}
                    {entry.message && <div className="form-error">{entry.message}</div>}
                  </td>
                  <td className="muted">{entry.client_address ?? ""}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      {loading && <Loading />}
      {hasMore && !loading && (
        <button type="button" className="button" onClick={() => load(entries[entries.length - 1]?.id, true)}>
          Показать ещё
        </button>
      )}
    </div>
  );
}
