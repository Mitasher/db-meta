import type { CellValue } from "../types";

interface SimpleTableProps {
  columns: string[];
  rows: CellValue[][];
}

/** Таблица без метаданных — для результата SQL-консоли. */
export function SimpleTable({ columns, rows }: SimpleTableProps) {
  return (
    <div className="table-wrap">
      <table className="data-table">
        <thead>
          <tr>
            <th className="cell-index">#</th>
            {columns.map((column, index) => (
              <th key={index}>
                <span className="th-text">{column}</span>
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, rowIndex) => (
            <tr key={rowIndex}>
              <td className="cell-index">{rowIndex + 1}</td>
              {row.map((value, index) => (
                <td key={index} className={value === null ? "cell cell-null" : "cell"}>
                  <span className="cell-value">{value === null ? "NULL" : String(value)}</span>
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
