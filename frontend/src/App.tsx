import { useCallback, useState } from "react";
import { AdminPage } from "./pages/AdminPage";
import { HistoryPage } from "./pages/HistoryPage";
import { SqlConsolePage } from "./pages/SqlConsolePage";
import { TablesPage } from "./pages/TablesPage";
import { TemplatesPage } from "./pages/TemplatesPage";
import { useRoute, type Route } from "./utils/routing";

const NAV_ITEMS: { name: Route["name"]; href: string; label: string }[] = [
  { name: "tables", href: "#/tables", label: "Таблицы" },
  { name: "templates", href: "#/templates", label: "Шаблоны" },
  { name: "sql", href: "#/sql", label: "SQL-консоль" },
  { name: "history", href: "#/history", label: "История" },
  { name: "admin", href: "#/admin", label: "Админка" },
];

/** Оболочка: навигация и текущий экран. */
export function App() {
  const route = useRoute();
  // Растёт после изменений из SQL-консоли — экраны с данными перечитывают их
  const [dataVersion, setDataVersion] = useState(0);
  const onDataChanged = useCallback(() => setDataVersion((version) => version + 1), []);

  return (
    <div className="app">
      <header className="topbar">
        <a className="brand" href="#/tables">
          bd_meta
        </a>
        <nav className="topnav">
          {NAV_ITEMS.map((item) => (
            <a key={item.name} href={item.href} className={route.name === item.name ? "topnav-item active" : "topnav-item"}>
              {item.label}
            </a>
          ))}
        </nav>
      </header>
      <main className="main">
        {route.name === "tables" && (
          <TablesPage tableId={route.tableId} templateId={route.templateId} dataVersion={dataVersion} />
        )}
        {route.name === "templates" && <TemplatesPage />}
        {route.name === "sql" && <SqlConsolePage onDataChanged={onDataChanged} />}
        {route.name === "history" && <HistoryPage />}
        {route.name === "admin" && <AdminPage tableId={route.tableId} />}
      </main>
    </div>
  );
}
