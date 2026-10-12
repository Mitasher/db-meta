import { useState } from "react";
import { getTables } from "../api";
import { EmptyState, ErrorMessage, Loading } from "../components/StateView";
import { tableHref } from "../utils/routing";
import { useLoad } from "../utils/useLoad";
import { TableView } from "./TableView";

interface TablesPageProps {
  tableId: number | null;
  templateId: number | null;
  dataVersion: number;
}

/** Экран «Таблицы»: список слева, данные выбранной таблицы справа. */
export function TablesPage({ tableId, templateId, dataVersion }: TablesPageProps) {
  const tables = useLoad(getTables, []);
  const [search, setSearch] = useState("");
  const needle = search.trim().toLowerCase();
  const visible = (tables.data ?? []).filter(
    (table) => !needle || table.label.toLowerCase().includes(needle) || table.name.toLowerCase().includes(needle),
  );

  return (
    <div className="split">
      <aside className="sidebar">
        <input
          className="input sidebar-search"
          type="search"
          placeholder="Найти таблицу"
          value={search}
          onChange={(event) => setSearch(event.target.value)}
          aria-label="Поиск таблицы"
        />
        {tables.loading && !tables.data && <Loading />}
        {tables.error && <ErrorMessage message={tables.error} onRetry={tables.reload} />}
        {tables.data && visible.length === 0 && (
          <EmptyState text={needle ? "Ничего не найдено" : "Нет видимых таблиц — включите их в админке"} />
        )}
        <nav className="sidebar-list">
          {visible.map((table) => (
            <a
              key={table.id}
              href={tableHref(table.id)}
              className={table.id === tableId ? "sidebar-item active" : "sidebar-item"}
              title={`${table.schema_name}.${table.name}`}
            >
              <span>{table.label}</span>
              {table.label !== table.name && <span className="sidebar-item-sub">{table.name}</span>}
            </a>
          ))}
        </nav>
      </aside>
      <section className="content">
        {tableId === null ? (
          <EmptyState text="Выберите таблицу слева" />
        ) : (
          <TableView
            key={`${tableId}:${templateId ?? ""}`}
            tableId={tableId}
            templateId={templateId}
            dataVersion={dataVersion}
          />
        )}
      </section>
    </div>
  );
}
