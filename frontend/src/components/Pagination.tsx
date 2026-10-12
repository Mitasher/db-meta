import { useState } from "react";

interface PaginationProps {
  page: number;
  pageSize: number;
  total: number;
  onPageChange: (page: number) => void;
  onPageSizeChange: (pageSize: number) => void;
}

interface PageInputProps {
  page: number;
  pageCount: number;
  onPageChange: (page: number) => void;
}

// Не больше 500 — потолок бэкенда
const PAGE_SIZES = [25, 50, 100, 200, 500];

/** Номер страницы: переход по Enter или при уходе с поля, а не на каждую цифру. */
function PageInput({ page, pageCount, onPageChange }: PageInputProps) {
  const [text, setText] = useState(String(page));

  const commit = () => {
    const next = Number(text);
    if (Number.isInteger(next) && next >= 1 && next <= pageCount && next !== page) {
      onPageChange(next);
    } else {
      setText(String(page));
    }
  };

  return (
    <input
      className="input input-page"
      type="number"
      min={1}
      max={pageCount}
      value={text}
      onChange={(event) => setText(event.target.value)}
      onBlur={commit}
      onKeyDown={(event) => event.key === "Enter" && commit()}
      aria-label="Номер страницы"
    />
  );
}

/** Переключение страниц и размера страницы. */
export function Pagination({ page, pageSize, total, onPageChange, onPageSizeChange }: PaginationProps) {
  const pageCount = Math.max(1, Math.ceil(total / pageSize));
  const first = total === 0 ? 0 : (page - 1) * pageSize + 1;
  const last = Math.min(total, page * pageSize);

  return (
    <div className="pagination">
      <span className="pagination-info">
        {first}–{last} из {total.toLocaleString("ru-RU")}
      </span>
      <div className="pagination-controls">
        <button type="button" className="button button-small" onClick={() => onPageChange(1)} disabled={page <= 1}>
          «
        </button>
        <button
          type="button"
          className="button button-small"
          onClick={() => onPageChange(page - 1)}
          disabled={page <= 1}
        >
          ‹
        </button>
        <span className="pagination-page">
          стр. <PageInput key={page} page={page} pageCount={pageCount} onPageChange={onPageChange} /> из{" "}
          {pageCount}
        </span>
        <button
          type="button"
          className="button button-small"
          onClick={() => onPageChange(page + 1)}
          disabled={page >= pageCount}
        >
          ›
        </button>
        <button
          type="button"
          className="button button-small"
          onClick={() => onPageChange(pageCount)}
          disabled={page >= pageCount}
        >
          »
        </button>
        <select
          className="input input-small"
          value={pageSize}
          onChange={(event) => onPageSizeChange(Number(event.target.value))}
          aria-label="Строк на странице"
        >
          {PAGE_SIZES.map((size) => (
            <option key={size} value={size}>
              по {size}
            </option>
          ))}
        </select>
      </div>
    </div>
  );
}
