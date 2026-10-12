import { useEffect, useRef, useState, type FormEvent } from "react";
import type { CellValue, Column, Filter, FilterOperator, TypeGroup } from "../types";
import { fromInputValue } from "../utils/values";
import { ValueInput } from "./ValueInput";

interface FilterBuilderProps {
  columns: Column[];
  filters: Filter[];
  onApply: (filters: Filter[]) => void;
}

interface DraftFilter {
  key: number;
  column: string;
  operator: FilterOperator;
  value: string;
  valueTo: string;
}

const OPERATOR_LABELS: Record<FilterOperator, string> = {
  eq: "=",
  ne: "≠",
  gt: ">",
  lt: "<",
  between: "от … до",
  like: "содержит",
  in: "одно из",
  is_null: "пусто",
  is_not_null: "не пусто",
};

/** Оператор, с которого удобно начинать для типа: число и дата — диапазон, строка — поиск. */
function defaultOperator(column: Column): FilterOperator {
  const preferred: Record<TypeGroup, FilterOperator> = {
    integer: "between",
    number: "between",
    date: "between",
    datetime: "between",
    string: "like",
    boolean: "eq",
    other: "is_null",
  };
  const operator = preferred[column.type_group];
  return column.operators.includes(operator) ? operator : column.operators[0];
}

/** Значение фильтра строкой для поля ввода. */
function valueText(value: CellValue | undefined): string {
  return value === null || value === undefined ? "" : String(value);
}

/** Применённый фильтр в черновик формы. */
function toDraft(filter: Filter, key: number): DraftFilter {
  const draft: DraftFilter = { key, column: filter.column, operator: filter.operator, value: "", valueTo: "" };
  if (Array.isArray(filter.value)) {
    if (filter.operator === "between") {
      draft.value = valueText(filter.value[0]);
      draft.valueTo = valueText(filter.value[1]);
    } else {
      draft.value = filter.value.map(valueText).join(", ");
    }
  } else if (filter.operator === "like" && typeof filter.value === "string") {
    // Обёртку %…% форма добавляет сама — показываем без неё
    draft.value = filter.value.replace(/^%(.*)%$/, "$1");
  } else {
    draft.value = valueText(filter.value);
  }
  return draft;
}

/** Черновик в фильтр для бэкенда; строка — текст ошибки, если значение не заполнено. */
function fromDraft(draft: DraftFilter, column: Column): Filter | string {
  const { operator } = draft;
  const label = column.label;
  if (operator === "is_null" || operator === "is_not_null") {
    return { column: draft.column, operator };
  }
  if (operator === "between") {
    if (draft.value === "" || draft.valueTo === "") {
      return `«${label}»: укажите обе границы`;
    }
    return {
      column: draft.column,
      operator,
      value: [fromInputValue(draft.value, column.type_group), fromInputValue(draft.valueTo, column.type_group)],
    };
  }
  if (operator === "in") {
    const items = draft.value
      .split(",")
      .map((item) => item.trim())
      .filter(Boolean);
    if (items.length === 0) {
      return `«${label}»: перечислите значения через запятую`;
    }
    return { column: draft.column, operator, value: items };
  }
  if (draft.value === "") {
    return `«${label}»: укажите значение`;
  }
  if (operator === "like") {
    // Без % и _ ищем подстроку; с ними — как написал пользователь
    const pattern = /[%_]/.test(draft.value) ? draft.value : `%${draft.value}%`;
    return { column: draft.column, operator, value: pattern };
  }
  return { column: draft.column, operator, value: fromInputValue(draft.value, column.type_group) };
}

/** Форма фильтров: поля ввода строятся по типам колонок из метаданных. */
export function FilterBuilder({ columns, filters, onApply }: FilterBuilderProps) {
  const nextKey = useRef(0);
  const [drafts, setDrafts] = useState<DraftFilter[]>([]);
  const [error, setError] = useState<string | null>(null);
  const columnsByName = new Map(columns.map((column) => [column.name, column]));

  useEffect(() => {
    setDrafts(filters.map((filter) => toDraft(filter, nextKey.current++)));
    setError(null);
  }, [filters]);

  const change = (key: number, patch: Partial<DraftFilter>) =>
    setDrafts((current) => current.map((draft) => (draft.key === key ? { ...draft, ...patch } : draft)));

  const changeColumn = (key: number, name: string) => {
    const column = columnsByName.get(name);
    if (column) {
      change(key, { column: name, operator: defaultOperator(column), value: "", valueTo: "" });
    }
  };

  const add = () => {
    const column = columns[0];
    if (column) {
      setDrafts((current) => [
        ...current,
        { key: nextKey.current++, column: column.name, operator: defaultOperator(column), value: "", valueTo: "" },
      ]);
    }
  };

  const apply = (next: DraftFilter[]) => {
    const result: Filter[] = [];
    for (const draft of next) {
      const column = columnsByName.get(draft.column);
      if (!column) {
        continue;
      }
      const filter = fromDraft(draft, column);
      if (typeof filter === "string") {
        setError(filter);
        return;
      }
      result.push(filter);
    }
    setError(null);
    onApply(result);
  };

  const submit = (event: FormEvent) => {
    event.preventDefault();
    apply(drafts);
  };

  if (columns.length === 0) {
    return null;
  }

  return (
    <form className="filters" onSubmit={submit}>
      {drafts.map((draft) => {
        const column = columnsByName.get(draft.column);
        if (!column) {
          return null;
        }
        const group = column.type_group;
        const needsValue = draft.operator !== "is_null" && draft.operator !== "is_not_null";
        return (
          <div className="filter-row" key={draft.key}>
            <select
              className="input"
              value={draft.column}
              onChange={(event) => changeColumn(draft.key, event.target.value)}
              aria-label="Колонка"
            >
              {columns.map((item) => (
                <option key={item.name} value={item.name}>
                  {item.label}
                </option>
              ))}
            </select>
            <select
              className="input input-operator"
              value={draft.operator}
              onChange={(event) => change(draft.key, { operator: event.target.value as FilterOperator })}
              aria-label="Условие"
            >
              {column.operators.map((operator) => (
                <option key={operator} value={operator}>
                  {OPERATOR_LABELS[operator]}
                </option>
              ))}
            </select>
            {needsValue && draft.operator === "in" && (
              <input
                className="input input-grow"
                value={draft.value}
                placeholder="значения через запятую"
                onChange={(event) => change(draft.key, { value: event.target.value })}
                aria-label="Значения"
              />
            )}
            {needsValue && draft.operator === "between" && (
              <>
                <ValueInput
                  group={group}
                  value={draft.value}
                  placeholder="от"
                  onChange={(value) => change(draft.key, { value })}
                  ariaLabel="От"
                />
                <ValueInput
                  group={group}
                  value={draft.valueTo}
                  placeholder="до"
                  onChange={(valueTo) => change(draft.key, { valueTo })}
                  ariaLabel="До"
                />
              </>
            )}
            {needsValue && draft.operator !== "in" && draft.operator !== "between" && (
              <ValueInput
                group={draft.operator === "like" ? "string" : group}
                value={draft.value}
                placeholder={draft.operator === "like" ? "текст или шаблон с %" : "значение"}
                onChange={(value) => change(draft.key, { value })}
                className="input input-grow"
                emptyOption={group === "boolean" ? "—" : undefined}
                ariaLabel="Значение"
              />
            )}
            <button
              type="button"
              className="button button-icon"
              title="Убрать условие"
              onClick={() => setDrafts((current) => current.filter((item) => item.key !== draft.key))}
            >
              ×
            </button>
          </div>
        );
      })}
      {error && <div className="form-error">{error}</div>}
      <div className="filters-actions">
        <button type="button" className="button button-small" onClick={add}>
          + Условие
        </button>
        <button type="submit" className="button button-small button-primary">
          Применить
        </button>
        {(drafts.length > 0 || filters.length > 0) && (
          <button
            type="button"
            className="button button-small"
            onClick={() => {
              setDrafts([]);
              apply([]);
            }}
          >
            Сбросить
          </button>
        )}
      </div>
    </form>
  );
}
