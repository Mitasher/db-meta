import { useCallback, useEffect, useState } from "react";
import { getAdminTable, getAdminTables, getSources, saveAdminTable, syncSource } from "../api";
import { Notice, type NoticeData } from "../components/Notice";
import { EmptyState, ErrorMessage, Loading } from "../components/StateView";
import type { AdminColumn, AdminTable, AdminTableDetail, SyncResult } from "../types";
import { errorText, useLoad } from "../utils/useLoad";

interface AdminPageProps {
  tableId: number | null;
}

interface TableEditorProps {
  tableId: number;
  version: number;
  onSaved: (table: AdminTable) => void;
}

interface TableForm {
  label: string;
  is_visible: boolean;
  is_editable: boolean;
  allow_insert: boolean;
  allow_delete: boolean;
  columns: AdminColumn[];
}

type ColumnFlag = "is_visible" | "is_filterable" | "is_editable";

/** Форма из ответа бэкенда. */
function toForm(detail: AdminTableDetail): TableForm {
  return {
    label: detail.label ?? "",
    is_visible: detail.is_visible,
    is_editable: detail.is_editable,
    allow_insert: detail.allow_insert,
    allow_delete: detail.allow_delete,
    columns: detail.columns,
  };
}

/** Итог синхронизации одной строкой. */
function describeSync(result: SyncResult): string {
  const { tables, columns } = result;
  return (
    `Синхронизировано: таблицы +${tables.added} / изменено ${tables.updated} / пропало ${tables.deactivated}; ` +
    `колонки +${columns.added} / изменено ${columns.updated} / пропало ${columns.deactivated}`
  );
}

/** Настройка одной таблицы и её колонок. */
function TableEditor({ tableId, version, onSaved }: TableEditorProps) {
  const detail = useLoad(() => getAdminTable(tableId), [tableId, version]);
  const [form, setForm] = useState<TableForm | null>(null);
  const [saving, setSaving] = useState(false);
  const [notice, setNotice] = useState<NoticeData | null>(null);
  const closeNotice = useCallback(() => setNotice(null), []);

  useEffect(() => {
    if (detail.data) {
      setForm(toForm(detail.data));
    }
  }, [detail.data]);

  if (detail.loading && !detail.data) {
    return <Loading />;
  }
  if (detail.error || !detail.data) {
    return <ErrorMessage message={detail.error ?? "Таблица не загрузилась"} onRetry={detail.reload} />;
  }
  if (!form) {
    return <Loading />;
  }

  const table = detail.data;
  const dirty = JSON.stringify(form) !== JSON.stringify(toForm(table));

  const patch = (update: Partial<TableForm>) => setForm({ ...form, ...update });
  const patchColumn = (id: number, flag: ColumnFlag | "label", value: boolean | string) =>
    patch({ columns: form.columns.map((column) => (column.id === id ? { ...column, [flag]: value } : column)) });
  const setAll = (flag: ColumnFlag, value: boolean) =>
    patch({ columns: form.columns.map((column) => ({ ...column, [flag]: value })) });

  const move = (index: number, delta: number) => {
    const target = index + delta;
    if (target < 0 || target >= form.columns.length) {
      return;
    }
    const columns = [...form.columns];
    [columns[index], columns[target]] = [columns[target], columns[index]];
    patch({ columns });
  };

  const save = async () => {
    setSaving(true);
    try {
      const saved = await saveAdminTable(tableId, {
        label: form.label.trim() || null,
        is_visible: form.is_visible,
        is_editable: form.is_editable,
        allow_insert: form.allow_insert,
        allow_delete: form.allow_delete,
        columns: form.columns.map((column) => ({
          id: column.id,
          label: column.label?.trim() || null,
          is_visible: column.is_visible,
          is_filterable: column.is_filterable,
          is_editable: column.is_editable,
        })),
      });
      detail.setData(() => saved);
      onSaved(saved);
      setNotice({ kind: "success", text: "Настройки сохранены" });
    } catch (error) {
      setNotice({ kind: "error", text: `Не сохранено: ${errorText(error)}` });
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="admin-editor">
      <header className="view-header">
        <div>
          <h1 className="view-title">{table.label || table.name}</h1>
          <div className="view-subtitle">
            {table.schema_name}.{table.name}
            {!table.is_active && <span className="badge badge-danger">нет в источнике</span>}
          </div>
        </div>
        <div className="toolbar">
          <button type="button" className="button button-small" onClick={() => setForm(toForm(table))} disabled={!dirty || saving}>
            Отменить изменения
          </button>
          <button type="button" className="button button-small button-primary" onClick={save} disabled={!dirty || saving}>
            {saving ? "Сохранение…" : "Сохранить"}
          </button>
        </div>
      </header>
      <Notice notice={notice} onClose={closeNotice} />

      <div className="admin-table-form">
        <label className="field">
          <span>Подпись таблицы</span>
          <input
            className="input"
            value={form.label}
            placeholder={table.name}
            maxLength={255}
            onChange={(event) => patch({ label: event.target.value })}
          />
        </label>
        <div className="flag-group">
          <label className="checkbox">
            <input type="checkbox" checked={form.is_visible} onChange={(event) => patch({ is_visible: event.target.checked })} />
            Показывать в списке
          </label>
          <label className="checkbox">
            <input type="checkbox" checked={form.is_editable} onChange={(event) => patch({ is_editable: event.target.checked })} />
            Можно править строки
          </label>
          <label className="checkbox">
            <input
              type="checkbox"
              checked={form.allow_insert}
              disabled={!form.is_editable}
              onChange={(event) => patch({ allow_insert: event.target.checked })}
            />
            Добавление строк
          </label>
          <label className="checkbox">
            <input
              type="checkbox"
              checked={form.allow_delete}
              disabled={!form.is_editable}
              onChange={(event) => patch({ allow_delete: event.target.checked })}
            />
            Удаление строк
          </label>
        </div>
        {form.is_editable && table.primary_key_problem && (
          <div className="form-error">Править не получится: {table.primary_key_problem}</div>
        )}
      </div>

      <div className="table-wrap">
        <table className="data-table admin-columns">
          <thead>
            <tr>
              <th>Порядок</th>
              <th>Колонка</th>
              <th>Подпись</th>
              <th>
                <button type="button" className="th-button" title="Переключить у всех" onClick={() => setAll("is_visible", !form.columns.every((c) => c.is_visible))}>
                  Видна
                </button>
              </th>
              <th>
                <button type="button" className="th-button" title="Переключить у всех" onClick={() => setAll("is_filterable", !form.columns.every((c) => c.is_filterable))}>
                  Фильтр
                </button>
              </th>
              <th>
                <button type="button" className="th-button" title="Переключить у всех" onClick={() => setAll("is_editable", !form.columns.every((c) => c.is_editable))}>
                  Правка
                </button>
              </th>
              <th>Тип</th>
            </tr>
          </thead>
          <tbody>
            {form.columns.map((column, index) => (
              <tr key={column.id} className={column.is_active ? undefined : "row-inactive"}>
                <td className="cell-order">
                  <button type="button" className="button button-tiny" onClick={() => move(index, -1)} disabled={index === 0} title="Выше">
                    ↑
                  </button>
                  <button
                    type="button"
                    className="button button-tiny"
                    onClick={() => move(index, 1)}
                    disabled={index === form.columns.length - 1}
                    title="Ниже"
                  >
                    ↓
                  </button>
                </td>
                <td>
                  <code>{column.name}</code>
                  {column.is_primary_key && <span className="badge badge-key">PK</span>}
                  {!column.is_active && <span className="badge badge-danger">нет в источнике</span>}
                </td>
                <td>
                  <input
                    className="input input-cell"
                    value={column.label ?? ""}
                    placeholder={column.name}
                    maxLength={255}
                    onChange={(event) => patchColumn(column.id, "label", event.target.value)}
                    aria-label={`Подпись ${column.name}`}
                  />
                </td>
                <td className="cell-center">
                  <input type="checkbox" checked={column.is_visible} onChange={(event) => patchColumn(column.id, "is_visible", event.target.checked)} aria-label="Видна" />
                </td>
                <td className="cell-center">
                  <input type="checkbox" checked={column.is_filterable} onChange={(event) => patchColumn(column.id, "is_filterable", event.target.checked)} aria-label="Фильтр" />
                </td>
                <td className="cell-center">
                  <input
                    type="checkbox"
                    checked={column.is_editable}
                    disabled={column.is_primary_key}
                    title={column.is_primary_key ? "Первичный ключ менять нельзя" : undefined}
                    onChange={(event) => patchColumn(column.id, "is_editable", event.target.checked)}
                    aria-label="Правка"
                  />
                </td>
                <td className="muted" title={column.default_value ? `по умолчанию: ${column.default_value}` : undefined}>
                  {column.data_type.split(" ")[0]}
                  {!column.is_nullable && " · NOT NULL"}
                  {column.is_autoincrement && " · авто"}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

/** Экран «Админка»: синхронизация источников и настройка таблиц. */
export function AdminPage({ tableId }: AdminPageProps) {
  const sources = useLoad(getSources, []);
  const tables = useLoad(getAdminTables, []);
  const [syncingId, setSyncingId] = useState<number | null>(null);
  const [syncVersion, setSyncVersion] = useState(0);
  const [notice, setNotice] = useState<NoticeData | null>(null);
  const closeNotice = useCallback(() => setNotice(null), []);

  const sync = async (sourceId: number) => {
    setSyncingId(sourceId);
    try {
      const result = await syncSource(sourceId);
      setNotice({ kind: "success", text: describeSync(result) });
      sources.reload();
      tables.reload();
      setSyncVersion((version) => version + 1);
    } catch (error) {
      setNotice({ kind: "error", text: `Синхронизация не удалась: ${errorText(error)}` });
    } finally {
      setSyncingId(null);
    }
  };

  const onSaved = (saved: AdminTable) =>
    tables.setData((current) => (current ? current.map((table) => (table.id === saved.id ? saved : table)) : current));

  return (
    <div className="split">
      <aside className="sidebar">
        <div className="sidebar-section">
          {sources.error && <ErrorMessage message={sources.error} onRetry={sources.reload} />}
          {(sources.data ?? []).map((source) => (
            <div key={source.id} className="source-card">
              <div className="source-name">{source.name}</div>
              <div className="muted">
                {source.db_type} · {source.host}:{source.port}/{source.database}
              </div>
              <div className="muted">
                {source.last_synced_at
                  ? `синхр. ${new Date(source.last_synced_at).toLocaleString("ru-RU")}`
                  : "ещё не синхронизирован"}
              </div>
              <button
                type="button"
                className="button button-small button-primary"
                onClick={() => sync(source.id)}
                disabled={syncingId !== null}
              >
                {syncingId === source.id ? "Синхронизация…" : "Синхронизировать"}
              </button>
            </div>
          ))}
        </div>
        {tables.loading && !tables.data && <Loading />}
        {tables.error && <ErrorMessage message={tables.error} onRetry={tables.reload} />}
        <nav className="sidebar-list">
          {(tables.data ?? []).map((table) => (
            <a
              key={table.id}
              href={`#/admin/${table.id}`}
              className={["sidebar-item", table.id === tableId ? "active" : "", table.is_active ? "" : "inactive"].join(" ")}
            >
              <span>{table.label || table.name}</span>
              <span className="sidebar-item-flags">
                {!table.is_visible && <span className="badge badge-muted">скрыта</span>}
                {table.is_editable && <span className="badge badge-ok">правка</span>}
                {!table.is_active && <span className="badge badge-danger">нет</span>}
              </span>
            </a>
          ))}
        </nav>
      </aside>
      <section className="content">
        <Notice notice={notice} onClose={closeNotice} />
        {tableId === null ? (
          <EmptyState text="Выберите таблицу, чтобы настроить подписи, видимость, порядок колонок и редактирование" />
        ) : (
          <TableEditor key={tableId} tableId={tableId} version={syncVersion} onSaved={onSaved} />
        )}
      </section>
    </div>
  );
}
