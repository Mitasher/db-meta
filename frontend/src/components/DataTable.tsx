import { useState, type KeyboardEvent } from "react";
import type { CellValue, Column, Row, Sort } from "../types";
import { formatValue, fromInputValue, sameValue, toInputValue } from "../utils/values";
import { ValueInput } from "./ValueInput";

export interface CellStatus {
  status: "saving" | "saved" | "error";
  message?: string;
}

export interface InsertRowOptions {
  onSubmit: (values: Row) => Promise<boolean>;
  onCancel: () => void;
}

interface DataTableProps {
  columns: Column[];
  rows: Row[];
  rowKey: (row: Row, index: number) => string;
  sort: Sort[];
  onSortChange?: (sort: Sort[]) => void;
  canEditCell?: (column: Column) => boolean;
  cellStatus?: (row: Row, column: Column) => CellStatus | undefined;
  onCellSave?: (row: Row, column: Column, value: CellValue) => void;
  onRowDelete?: (row: Row) => void;
  insert?: InsertRowOptions | null;
}

interface CellEditorProps {
  column: Column;
  initial: CellValue;
  onCommit: (value: CellValue) => void;
  onCancel: () => void;
}

interface InsertRowProps {
  columns: Column[];
  hasActions: boolean;
  options: InsertRowOptions;
}

/** Значение из редактора: пустое поле не-строковой колонки — это NULL. */
function editorValue(text: string, column: Column): CellValue {
  if (text === "" && column.type_group !== "string") {
    return null;
  }
  return fromInputValue(text, column.type_group);
}

/** Поле правки ячейки: Enter сохраняет, Escape отменяет. */
function CellEditor({ column, initial, onCommit, onCancel }: CellEditorProps) {
  const [text, setText] = useState(() => toInputValue(initial, column.type_group));

  const onKeyDown = (event: KeyboardEvent<HTMLInputElement | HTMLSelectElement>) => {
    if (event.key === "Enter") {
      event.preventDefault();
      onCommit(editorValue(text, column));
    } else if (event.key === "Escape") {
      event.preventDefault();
      onCancel();
    }
  };

  return (
    <div className="cell-editor">
      <ValueInput
        group={column.type_group}
        value={text}
        onChange={setText}
        className="input input-cell"
        autoFocus
        onKeyDown={onKeyDown}
        onBlur={onCancel}
        ariaLabel={column.label}
      />
      {column.is_nullable && (
        <button
          type="button"
          className="button button-tiny"
          title="Записать NULL"
          // mousedown, а не click: иначе поле потеряет фокус и правка отменится раньше
          onMouseDown={(event) => {
            event.preventDefault();
            onCommit(null);
          }}
        >
          NULL
        </button>
      )}
    </div>
  );
}

/** Строка ввода новой записи; пустые поля не отправляются — сработает значение по умолчанию из БД. */
function InsertRow({ columns, hasActions, options }: InsertRowProps) {
  const [values, setValues] = useState<Record<string, string>>({});
  const [busy, setBusy] = useState(false);

  const submit = async () => {
    const row: Row = {};
    for (const column of columns) {
      const text = values[column.name] ?? "";
      if (column.is_insertable && text !== "") {
        row[column.name] = fromInputValue(text, column.type_group);
      }
    }
    setBusy(true);
    const saved = await options.onSubmit(row);
    setBusy(false);
    if (saved) {
      setValues({});
    }
  };

  const onKeyDown = (event: KeyboardEvent<HTMLInputElement | HTMLSelectElement>) => {
    if (event.key === "Enter") {
      event.preventDefault();
      void submit();
    } else if (event.key === "Escape") {
      options.onCancel();
    }
  };

  return (
    <tr className="insert-row">
      {columns.map((column) => (
        <td key={column.name}>
          {column.is_insertable ? (
            <ValueInput
              group={column.type_group}
              value={values[column.name] ?? ""}
              onChange={(value) => setValues((current) => ({ ...current, [column.name]: value }))}
              className={column.is_required ? "input input-cell input-required" : "input input-cell"}
              placeholder={column.is_required ? "обязательно" : ""}
              emptyOption="—"
              onKeyDown={onKeyDown}
              ariaLabel={column.label}
            />
          ) : (
            <span className="muted">{column.is_primary_key ? "авто" : "—"}</span>
          )}
        </td>
      ))}
      <td className={hasActions ? "cell-actions" : "cell-actions cell-actions-extra"}>
        <button type="button" className="button button-tiny button-primary" onClick={submit} disabled={busy}>
          {busy ? "…" : "Добавить"}
        </button>
        <button type="button" className="button button-tiny" onClick={options.onCancel} disabled={busy}>
          Отмена
        </button>
      </td>
    </tr>
  );
}

/** Следующее состояние сортировки по клику на заголовок: по возрастанию → по убыванию → без сортировки. */
function nextSort(sort: Sort[], column: string): Sort[] {
  const current = sort.find((item) => item.column === column);
  if (!current) {
    return [{ column, direction: "asc" }];
  }
  if (current.direction === "asc") {
    return [{ column, direction: "desc" }];
  }
  return [];
}

/** Универсальная таблица: колонки и правила правки берёт из метаданных, о предметной области ничего не знает. */
export function DataTable({
  columns,
  rows,
  rowKey,
  sort,
  onSortChange,
  canEditCell,
  cellStatus,
  onCellSave,
  onRowDelete,
  insert,
}: DataTableProps) {
  const [editing, setEditing] = useState<{ key: string; column: string } | null>(null);
  const hasActions = Boolean(onRowDelete);

  const commit = (row: Row, column: Column, value: CellValue) => {
    setEditing(null);
    if (!sameValue(row[column.name], value) && onCellSave) {
      onCellSave(row, column, value);
    }
  };

  return (
    <div className="table-wrap">
      <table className="data-table">
        <thead>
          <tr>
            {columns.map((column) => {
              const sorted = sort.find((item) => item.column === column.name);
              return (
                <th key={column.name} title={`${column.name} · ${column.data_type}`}>
                  <button
                    type="button"
                    className="th-button"
                    onClick={() => onSortChange?.(nextSort(sort, column.name))}
                    disabled={!onSortChange}
                  >
                    {column.label}
                    {column.is_primary_key && <span className="badge badge-key">PK</span>}
                    <span className="sort-mark">{sorted ? (sorted.direction === "asc" ? "▲" : "▼") : ""}</span>
                  </button>
                </th>
              );
            })}
            {(hasActions || insert) && <th className="cell-actions" />}
          </tr>
        </thead>
        <tbody>
          {insert && <InsertRow columns={columns} hasActions={hasActions} options={insert} />}
          {rows.map((row, index) => {
            const key = rowKey(row, index);
            return (
              <tr key={key}>
                {columns.map((column) => {
                  const value = row[column.name];
                  const editable = canEditCell ? canEditCell(column) : false;
                  const status = cellStatus?.(row, column);
                  const isEditing = editing !== null && editing.key === key && editing.column === column.name;
                  const classes = ["cell", `cell-${column.type_group}`];
                  if (canEditCell && !editable) {
                    classes.push("cell-readonly");
                  }
                  if (editable) {
                    classes.push("cell-editable");
                  }
                  if (value === null || value === undefined) {
                    classes.push("cell-null");
                  }
                  if (status) {
                    classes.push(`cell-${status.status}`);
                  }
                  return (
                    <td
                      key={column.name}
                      className={classes.join(" ")}
                      title={status?.status === "error" ? status.message : editable ? "Двойной клик — изменить" : undefined}
                      onDoubleClick={() => editable && setEditing({ key, column: column.name })}
                    >
                      {isEditing ? (
                        <CellEditor
                          column={column}
                          initial={value ?? null}
                          onCommit={(next) => commit(row, column, next)}
                          onCancel={() => setEditing(null)}
                        />
                      ) : (
                        <>
                          <span className="cell-value">{formatValue(value, column.type_group)}</span>
                          {status && <span className={`cell-status cell-status-${status.status}`} aria-hidden="true" />}
                        </>
                      )}
                    </td>
                  );
                })}
                {(hasActions || insert) && (
                  <td className="cell-actions">
                    {onRowDelete && (
                      <button
                        type="button"
                        className="button button-tiny button-ghost-danger"
                        title="Удалить строку"
                        onClick={() => onRowDelete(row)}
                      >
                        Удалить
                      </button>
                    )}
                  </td>
                )}
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
