import { useEffect, useState } from "react";

export type Route =
  | { name: "tables"; tableId: number | null; templateId: number | null }
  | { name: "templates" }
  | { name: "sql" }
  | { name: "admin"; tableId: number | null }
  | { name: "history" };

/** Число из части адреса; null — если там не число. */
function parseId(value: string | null | undefined): number | null {
  if (!value || !/^\d+$/.test(value)) {
    return null;
  }
  return Number(value);
}

/** Экран по hash-части адреса: #/tables/7?template=3. */
export function parseRoute(hash: string): Route {
  const [path, search] = hash.replace(/^#/, "").split("?");
  const parts = path.split("/").filter(Boolean);
  const params = new URLSearchParams(search ?? "");
  if (parts[0] === "templates") {
    return { name: "templates" };
  }
  if (parts[0] === "sql") {
    return { name: "sql" };
  }
  if (parts[0] === "admin") {
    return { name: "admin", tableId: parseId(parts[1]) };
  }
  if (parts[0] === "history") {
    return { name: "history" };
  }
  return { name: "tables", tableId: parseId(parts[1]), templateId: parseId(params.get("template")) };
}

/** Адрес экрана таблицы, с шаблоном или без. */
export function tableHref(tableId: number, templateId?: number | null): string {
  return templateId ? `#/tables/${tableId}?template=${templateId}` : `#/tables/${tableId}`;
}

/** Переход на другой экран. */
export function navigate(href: string): void {
  window.location.hash = href.replace(/^#/, "");
}

/** Текущий экран; меняется вместе с адресом. */
export function useRoute(): Route {
  const [route, setRoute] = useState(() => parseRoute(window.location.hash));
  useEffect(() => {
    const onChange = () => setRoute(parseRoute(window.location.hash));
    window.addEventListener("hashchange", onChange);
    return () => window.removeEventListener("hashchange", onChange);
  }, []);
  return route;
}
