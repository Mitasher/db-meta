// Запросы к бэкенду: только транспорт, без логики экранов
import type {
  AdminTable,
  AdminTableDetail,
  AdminTableInput,
  ChangeLogEntry,
  ChangeLogQuery,
  DataPage,
  DataQuery,
  ExportRequest,
  Row,
  RowResponse,
  RowUpdate,
  Source,
  SqlExecuteInput,
  SqlResult,
  SqlStatus,
  SyncResult,
  TableMeta,
  TableSummary,
  Template,
  TemplateInput,
} from "./types";

/** Ошибка от бэкенда с кодом ответа и понятным текстом. */
export class ApiError extends Error {
  status: number;

  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

interface ValidationIssue {
  loc?: (string | number)[];
  msg?: string;
}

/** Текст ошибки из ответа FastAPI: detail строкой или списком ошибок валидации. */
function describeError(status: number, payload: unknown): string {
  if (payload && typeof payload === "object" && "detail" in payload) {
    const detail = (payload as { detail: unknown }).detail;
    if (typeof detail === "string") {
      return detail;
    }
    if (Array.isArray(detail)) {
      return (detail as ValidationIssue[])
        .map((issue) => {
          const place = (issue.loc ?? []).filter((part) => part !== "body").join(".");
          return place ? `${place}: ${issue.msg}` : issue.msg ?? "";
        })
        .join("; ");
    }
  }
  if (status === 502 || status === 503 || status === 504) {
    return `Сервер недоступен (${status}), попробуйте позже`;
  }
  return `Сервер вернул ошибку ${status}`;
}

/** Ответ с ошибкой в ApiError. */
async function failure(response: Response): Promise<ApiError> {
  let payload: unknown = null;
  try {
    payload = await response.json();
  } catch {
    payload = null;
  }
  return new ApiError(response.status, describeError(response.status, payload));
}

/** Выполняет запрос к /api; при сетевой ошибке тоже бросает ApiError. */
async function send(method: string, path: string, body?: unknown): Promise<Response> {
  let response: Response;
  try {
    response = await fetch(`/api${path}`, {
      method,
      headers: body === undefined ? undefined : { "Content-Type": "application/json" },
      body: body === undefined ? undefined : JSON.stringify(body),
    });
  } catch {
    throw new ApiError(0, "Нет связи с сервером");
  }
  if (!response.ok) {
    throw await failure(response);
  }
  return response;
}

/** Запрос с JSON-ответом. */
async function request<T>(method: string, path: string, body?: unknown): Promise<T> {
  const response = await send(method, path, body);
  if (response.status === 204) {
    return undefined as T;
  }
  return (await response.json()) as T;
}

/** Строка запроса из необязательных параметров. */
function queryString(params: Record<string, number | undefined>): string {
  const search = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined) {
      search.set(key, String(value));
    }
  }
  const text = search.toString();
  return text ? `?${text}` : "";
}

/** Имя файла из Content-Disposition: сначала UTF-8 вариант, потом обычный. */
function filenameFrom(header: string | null, fallback: string): string {
  if (!header) {
    return fallback;
  }
  const encoded = /filename\*=UTF-8''([^;]+)/i.exec(header);
  if (encoded) {
    return decodeURIComponent(encoded[1]);
  }
  const plain = /filename="([^"]+)"/i.exec(header);
  return plain ? plain[1] : fallback;
}

export function getSources(): Promise<Source[]> {
  return request("GET", "/sources");
}

export function syncSource(sourceId: number): Promise<SyncResult> {
  return request("POST", `/sources/${sourceId}/sync`);
}

export function getTables(): Promise<TableSummary[]> {
  return request("GET", "/tables");
}

export function getTableMeta(tableId: number): Promise<TableMeta> {
  return request("GET", `/tables/${tableId}/meta`);
}

export function getTableData(tableId: number, query: DataQuery): Promise<DataPage> {
  return request("POST", `/tables/${tableId}/data`, query);
}

export function updateRow(tableId: number, pk: string, update: RowUpdate): Promise<RowResponse> {
  return request("PATCH", `/tables/${tableId}/rows/${encodeURIComponent(pk)}`, update);
}

export function insertRow(tableId: number, values: Row): Promise<RowResponse> {
  return request("POST", `/tables/${tableId}/rows`, { values });
}

export function deleteRow(tableId: number, pk: string): Promise<void> {
  return request("DELETE", `/tables/${tableId}/rows/${encodeURIComponent(pk)}`);
}

export function getTemplates(): Promise<Template[]> {
  return request("GET", "/templates");
}

export function getTemplate(templateId: number): Promise<Template> {
  return request("GET", `/templates/${templateId}`);
}

export function createTemplate(template: TemplateInput): Promise<Template> {
  return request("POST", "/templates", template);
}

export function updateTemplate(templateId: number, template: TemplateInput): Promise<Template> {
  return request("PUT", `/templates/${templateId}`, template);
}

export function deleteTemplate(templateId: number): Promise<void> {
  return request("DELETE", `/templates/${templateId}`);
}

export async function exportExcel(exportRequest: ExportRequest): Promise<{ blob: Blob; filename: string }> {
  const response = await send("POST", "/export", exportRequest);
  return {
    blob: await response.blob(),
    filename: filenameFrom(response.headers.get("Content-Disposition"), "export.xlsx"),
  };
}

export function getSqlStatus(): Promise<SqlStatus> {
  return request("GET", "/sql/status");
}

export function executeSql(input: SqlExecuteInput): Promise<SqlResult> {
  return request("POST", "/sql/execute", input);
}

export function getChangeLog(query: ChangeLogQuery): Promise<ChangeLogEntry[]> {
  return request("GET", `/change-log${queryString({ ...query })}`);
}

export function getAdminTables(): Promise<AdminTable[]> {
  return request("GET", "/admin/tables");
}

export function getAdminTable(tableId: number): Promise<AdminTableDetail> {
  return request("GET", `/admin/tables/${tableId}`);
}

export function saveAdminTable(tableId: number, input: AdminTableInput): Promise<AdminTableDetail> {
  return request("PUT", `/admin/tables/${tableId}`, input);
}
