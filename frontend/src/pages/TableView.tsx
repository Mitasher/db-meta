import { useCallback, useEffect, useState } from "react";
import {
  createTemplate,
  deleteRow,
  exportExcel,
  getTableData,
  getTableMeta,
  getTemplate,
  insertRow,
  updateRow,
  updateTemplate,
} from "../api";
import { DataTable, type CellStatus } from "../components/DataTable";
import { ConfirmDialog, Dialog } from "../components/Dialog";
import { FilterBuilder } from "../components/FilterBuilder";
import { Notice, type NoticeData } from "../components/Notice";
import { Pagination } from "../components/Pagination";
import { EmptyState, ErrorMessage, Loading } from "../components/StateView";
import type { CellValue, Column, DataPage, DataQuery, Filter, Row, Sort, TableMeta, Template, TemplateBody } from "../types";
import { saveBlob } from "../utils/download";
import { navigate, tableHref } from "../utils/routing";
import { errorText, useLoad } from "../utils/useLoad";

interface TableViewProps {
  tableId: number;
  templateId: number | null;
  dataVersion: number;
}

interface ColumnPickerProps {
  columns: Column[];
  selected: string[] | null;
  onChange: (selected: string[] | null) => void;
}

interface SaveTemplateDialogProps {
  onSave: (name: string, description: string) => Promise<void>;
  onClose: () => void;
}

// Опрос открытой таблицы, чтобы видеть чужие правки
const AUTO_REFRESH_MS = 30_000;
// Сколько держится отметка «сохранено» у ячейки
const SAVED_MARK_MS = 2_000;

/** Ключ состояния ячейки. */
function cellKey(pk: CellValue, column: string): string {
  return `${String(pk)}\u0001${column}`;
}

/** Запрос данных по телу шаблона или по умолчанию. */
function initialQuery(body: TemplateBody | null): DataQuery {
  return {
    columns: body?.columns ?? null,
    filters: body?.filters ?? [],
    sort: body?.sort ?? [],
    page: 1,
    page_size: body?.page_size ?? 50,
  };
}

/** Тело шаблона из текущего запроса. */
function templateBody(query: DataQuery): TemplateBody {
  return {
    schema_version: 1,
    columns: query.columns,
    filters: query.filters,
    sort: query.sort,
    page_size: query.page_size,
  };
}

/** Выбор показываемых колонок; null — все. */
function ColumnPicker({ columns, selected, onChange }: ColumnPickerProps) {
  const chosen = new Set(selected ?? columns.map((column) => column.name));

  const toggle = (name: string) => {
    const next = new Set(chosen);
    if (next.has(name)) {
      next.delete(name);
    } else {
      next.add(name);
    }
    if (next.size === 0) {
      return;
    }
    const ordered = columns.map((column) => column.name).filter((columnName) => next.has(columnName));
    onChange(ordered.length === columns.length ? null : ordered);
  };

  return (
    <details className="dropdown">
      <summary className="button button-small">
        Колонки {selected ? `${selected.length}/${columns.length}` : ""}
      </summary>
      <div className="dropdown-menu">
        <button type="button" className="button button-tiny" onClick={() => onChange(null)}>
          Показать все
        </button>
        {columns.map((column) => (
          <label key={column.name} className="checkbox">
            <input type="checkbox" checked={chosen.has(column.name)} onChange={() => toggle(column.name)} />
            {column.label}
          </label>
        ))}
      </div>
    </details>
  );
}

/** Окно «Сохранить как шаблон». */
function SaveTemplateDialog({ onSave, onClose }: SaveTemplateDialogProps) {
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const save = async () => {
    setBusy(true);
    setError(null);
    try {
      await onSave(name.trim(), description.trim());
    } catch (reason) {
      setError(errorText(reason));
      setBusy(false);
    }
  };

  return (
    <Dialog
      title="Сохранить как шаблон"
      onClose={onClose}
      footer={
        <>
          <button type="button" className="button" onClick={onClose} disabled={busy}>
            Отмена
          </button>
          <button type="button" className="button button-primary" onClick={save} disabled={busy || !name.trim()}>
            {busy ? "Сохранение…" : "Сохранить"}
          </button>
        </>
      }
    >
      <p className="muted">В шаблон попадут фильтры, сортировка, выбранные колонки и размер страницы.</p>
      <label className="field">
        <span>Название</span>
        <input className="input" value={name} autoFocus maxLength={255} onChange={(event) => setName(event.target.value)} />
      </label>
      <label className="field">
        <span>Описание</span>
        <textarea
          className="input"
          rows={3}
          value={description}
          onChange={(event) => setDescription(event.target.value)}
        />
      </label>
      {error && <div className="form-error">{error}</div>}
    </Dialog>
  );
}

/** Данные одной таблицы: фильтры, сортировка, пагинация, правка, шаблоны и выгрузка. */
export function TableView({ tableId, templateId, dataVersion }: TableViewProps) {
  const meta = useLoad<TableMeta>(() => getTableMeta(tableId), [tableId]);
  const template = useLoad<Template | null>(
    () => (templateId === null ? Promise.resolve(null) : getTemplate(templateId)),
    [templateId],
  );
  const [query, setQuery] = useState<DataQuery | null>(null);
  const [refreshTick, setRefreshTick] = useState(0);
  const [cellStates, setCellStates] = useState<Record<string, CellStatus>>({});
  const [notice, setNotice] = useState<NoticeData | null>(null);
  const [inserting, setInserting] = useState(false);
  const [rowToDelete, setRowToDelete] = useState<Row | null>(null);
  const [deleting, setDeleting] = useState(false);
  const [savingTemplate, setSavingTemplate] = useState(false);
  const [exporting, setExporting] = useState(false);
  const [autoRefresh, setAutoRefresh] = useState(false);
  const closeNotice = useCallback(() => setNotice(null), []);

  // Запрос собирается один раз, когда шаблон загружен; сохранение шаблона его не сбрасывает
  useEffect(() => {
    if (!template.loading && !template.error) {
      setQuery(initialQuery(template.data?.body ?? null));
    }
  }, [template.loading, template.error]);

  const page = useLoad<DataPage | null>(
    () => (query === null || !meta.data ? Promise.resolve(null) : getTableData(tableId, query)),
    [tableId, query, meta.data, dataVersion, refreshTick],
  );

  useEffect(() => {
    if (!autoRefresh) {
      return;
    }
    const timer = setInterval(() => setRefreshTick((tick) => tick + 1), AUTO_REFRESH_MS);
    return () => clearInterval(timer);
  }, [autoRefresh]);

  if (meta.loading && !meta.data) {
    return <Loading />;
  }
  if (meta.error || !meta.data) {
    return <ErrorMessage message={meta.error ?? "Таблица не загрузилась"} onRetry={meta.reload} />;
  }
  if (template.error) {
    return <ErrorMessage message={`Шаблон не открылся: ${template.error}`} onRetry={template.reload} />;
  }
  if (template.data && template.data.table_id !== tableId) {
    return (
      <ErrorMessage
        message="Шаблон относится к другой таблице"
        onRetry={() => navigate(tableHref(template.data!.table_id, template.data!.id))}
      />
    );
  }

  const tableMeta = meta.data;
  const columnsByName = new Map(tableMeta.columns.map((column) => [column.name, column]));
  const shownColumns = (page.data?.columns ?? query?.columns ?? tableMeta.columns.map((column) => column.name))
    .map((name) => columnsByName.get(name))
    .filter((column): column is Column => column !== undefined);
  const pkColumn = tableMeta.columns.find((column) => column.is_primary_key) ?? null;
  const pkShown = pkColumn !== null && shownColumns.some((column) => column.name === pkColumn.name);
  const canEdit = tableMeta.can_update && pkShown;
  const canDelete = tableMeta.can_delete && pkShown;
  const filterable = tableMeta.columns.filter((column) => column.is_filterable);
  const hiddenRequired = tableMeta.columns.filter(
    (column) => column.is_required && column.is_insertable && !shownColumns.includes(column),
  );

  const changeQuery = (patch: Partial<DataQuery>) =>
    setQuery((current) => (current ? { ...current, page: 1, ...patch } : current));

  const setCellState = (key: string, state: CellStatus | null) =>
    setCellStates((current) => {
      const next = { ...current };
      if (state) {
        next[key] = state;
      } else {
        delete next[key];
      }
      return next;
    });

  /** Подменяет строку с заданным ключом. */
  const replaceRow = (pk: CellValue, update: (row: Row) => Row) =>
    page.setData((current) =>
      current
        ? { ...current, rows: current.rows.map((row) => (pkColumn && row[pkColumn.name] === pk ? update(row) : row)) }
        : current,
    );

  const saveCell = async (row: Row, column: Column, value: CellValue) => {
    if (!pkColumn) {
      return;
    }
    const pk = row[pkColumn.name];
    const oldValue = row[column.name] ?? null;
    const key = cellKey(pk, column.name);
    // Правка видна сразу, при ошибке откатывается
    replaceRow(pk, (current) => ({ ...current, [column.name]: value }));
    setCellState(key, { status: "saving" });
    try {
      const response = await updateRow(tableId, String(pk), {
        changes: { [column.name]: value },
        original: { [column.name]: oldValue },
      });
      // В ответе — строка, как она теперь в БД: триггеры и дефолты могли поменять значения
      replaceRow(pk, (current) => ({ ...current, ...response.row }));
      setCellState(key, { status: "saved" });
      setTimeout(() => setCellStates((current) => {
        if (current[key]?.status !== "saved") {
          return current;
        }
        const next = { ...current };
        delete next[key];
        return next;
      }), SAVED_MARK_MS);
    } catch (error) {
      replaceRow(pk, (current) => (current[column.name] === value ? { ...current, [column.name]: oldValue } : current));
      const message = errorText(error);
      setCellState(key, { status: "error", message });
      setNotice({ kind: "error", text: `«${column.label}» не сохранено: ${message}` });
    }
  };

  const insert = async (values: Row): Promise<boolean> => {
    try {
      await insertRow(tableId, values);
      setNotice({ kind: "success", text: "Строка добавлена" });
      // Меняются число строк и состав страницы — перечитываем её
      page.reload();
      return true;
    } catch (error) {
      setNotice({ kind: "error", text: `Строка не добавлена: ${errorText(error)}` });
      return false;
    }
  };

  const confirmDelete = async () => {
    if (!rowToDelete || !pkColumn) {
      return;
    }
    setDeleting(true);
    try {
      await deleteRow(tableId, String(rowToDelete[pkColumn.name]));
      setNotice({ kind: "success", text: "Строка удалена" });
      page.reload();
    } catch (error) {
      setNotice({ kind: "error", text: `Строка не удалена: ${errorText(error)}` });
    } finally {
      setDeleting(false);
      setRowToDelete(null);
    }
  };

  const download = async () => {
    if (!query) {
      return;
    }
    setExporting(true);
    try {
      const file = await exportExcel({
        table_id: tableId,
        query: { columns: query.columns, filters: query.filters, sort: query.sort },
      });
      saveBlob(file.blob, file.filename);
    } catch (error) {
      setNotice({ kind: "error", text: `Выгрузка не удалась: ${errorText(error)}` });
    } finally {
      setExporting(false);
    }
  };

  const saveAsTemplate = async (name: string, description: string) => {
    if (!query) {
      return;
    }
    const created = await createTemplate({
      table_id: tableId,
      name,
      description: description || null,
      body: templateBody(query),
    });
    setSavingTemplate(false);
    navigate(tableHref(tableId, created.id));
  };

  const saveTemplateChanges = async () => {
    if (!query || !template.data) {
      return;
    }
    try {
      const updated = await updateTemplate(template.data.id, {
        table_id: tableId,
        name: template.data.name,
        description: template.data.description,
        body: templateBody(query),
      });
      template.setData(() => updated);
      setNotice({ kind: "success", text: "Шаблон обновлён" });
    } catch (error) {
      setNotice({ kind: "error", text: `Шаблон не сохранён: ${errorText(error)}` });
    }
  };

  return (
    <div className="table-view">
      <header className="view-header">
        <div>
          <h1 className="view-title">{tableMeta.label}</h1>
          <div className="view-subtitle">
            {tableMeta.schema_name}.{tableMeta.name}
            {tableMeta.read_only_reason ? (
              <span className="badge badge-muted" title={tableMeta.read_only_reason}>
                только чтение
              </span>
            ) : (
              <span className="badge badge-ok">можно править</span>
            )}
          </div>
        </div>
        <div className="toolbar">
          <label className="checkbox" title="Перечитывать данные раз в 30 секунд, чтобы видеть чужие правки">
            <input type="checkbox" checked={autoRefresh} onChange={(event) => setAutoRefresh(event.target.checked)} />
            автообновление
          </label>
          <button type="button" className="button button-small" onClick={page.reload} disabled={page.loading}>
            Обновить
          </button>
          <button type="button" className="button button-small" onClick={() => setSavingTemplate(true)} disabled={!query}>
            Сохранить как шаблон
          </button>
          <button type="button" className="button button-small button-primary" onClick={download} disabled={exporting || !query}>
            {exporting ? "Готовим файл…" : "Скачать Excel"}
          </button>
        </div>
      </header>

      {template.data && (
        <div className="template-bar">
          <span>
            Шаблон <strong>«{template.data.name}»</strong>
            {template.data.description && <span className="muted"> — {template.data.description}</span>}
          </span>
          <div className="toolbar">
            <button type="button" className="button button-small" onClick={saveTemplateChanges}>
              Сохранить изменения в шаблон
            </button>
            <a className="button button-small" href={tableHref(tableId)}>
              Закрыть шаблон
            </a>
          </div>
          {template.data.problems.map((problem) => (
            <div key={problem} className="form-error">
              {problem}
            </div>
          ))}
        </div>
      )}

      {query && (
        <div className="query-bar">
          <FilterBuilder columns={filterable} filters={query.filters} onApply={(filters: Filter[]) => changeQuery({ filters })} />
          <ColumnPicker
            columns={tableMeta.columns}
            selected={query.columns}
            onChange={(columns) => changeQuery({ columns })}
          />
        </div>
      )}

      <div className="hint-bar">
        {tableMeta.read_only_reason && <span>{tableMeta.read_only_reason}</span>}
        {tableMeta.can_update && !pkShown && <span>Чтобы править строки, покажите колонку первичного ключа</span>}
        {canEdit && <span>Двойной клик по ячейке — изменить, Enter — сохранить, Escape — отменить</span>}
        {tableMeta.can_insert && !inserting && (
          <button type="button" className="button button-small" onClick={() => setInserting(true)}>
            + Добавить строку
          </button>
        )}
      </div>
      {inserting && hiddenRequired.length > 0 && (
        <div className="form-error">
          Обязательные колонки скрыты: {hiddenRequired.map((column) => column.label).join(", ")} — покажите их, чтобы
          добавить строку
        </div>
      )}

      <Notice
        notice={notice}
        onClose={closeNotice}
        action={
          notice?.kind === "error" && (
            <button type="button" className="button button-small" onClick={page.reload}>
              Обновить данные
            </button>
          )
        }
      />

      {page.error && <ErrorMessage message={page.error} onRetry={page.reload} />}
      {!page.data && !page.error && <Loading />}
      {page.data && (
        <div className={page.loading ? "data-area is-refreshing" : "data-area"}>
          <DataTable
            columns={shownColumns}
            rows={page.data.rows}
            rowKey={(row, index) => (pkShown && pkColumn ? String(row[pkColumn.name]) : String(index))}
            sort={query?.sort ?? []}
            onSortChange={(sort: Sort[]) => changeQuery({ sort })}
            canEditCell={tableMeta.read_only_reason === null ? (column) => canEdit && column.is_editable : undefined}
            cellStatus={(row, column) => (pkColumn ? cellStates[cellKey(row[pkColumn.name], column.name)] : undefined)}
            onCellSave={saveCell}
            onRowDelete={canDelete ? setRowToDelete : undefined}
            insert={inserting && pkColumn ? { onSubmit: insert, onCancel: () => setInserting(false) } : null}
          />
          {page.data.rows.length === 0 && (
            <EmptyState text={query?.filters.length ? "Под фильтры ничего не попало" : "В таблице нет строк"} />
          )}
          <Pagination
            page={page.data.page}
            pageSize={page.data.page_size}
            total={page.data.total}
            onPageChange={(next) => setQuery((current) => (current ? { ...current, page: next } : current))}
            onPageSizeChange={(pageSize) => changeQuery({ page_size: pageSize })}
          />
        </div>
      )}

      {rowToDelete && pkColumn && (
        <ConfirmDialog
          title="Удалить строку?"
          confirmText="Удалить"
          danger
          busy={deleting}
          onConfirm={confirmDelete}
          onCancel={() => setRowToDelete(null)}
        >
          Строка с {pkColumn.label} = <strong>{String(rowToDelete[pkColumn.name])}</strong> будет удалена из источника.
          Отменить это нельзя.
        </ConfirmDialog>
      )}
      {savingTemplate && <SaveTemplateDialog onSave={saveAsTemplate} onClose={() => setSavingTemplate(false)} />}
    </div>
  );
}
