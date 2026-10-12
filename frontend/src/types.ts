// Типы ответов и запросов бэкенда — один источник правды для всего фронта

export type TypeGroup = "string" | "integer" | "number" | "date" | "datetime" | "boolean" | "other";

export type FilterOperator =
  | "eq"
  | "ne"
  | "gt"
  | "lt"
  | "between"
  | "like"
  | "in"
  | "is_null"
  | "is_not_null";

export type CellValue = string | number | boolean | null;
export type Row = Record<string, CellValue>;

export interface Source {
  id: number;
  name: string;
  db_type: string;
  host: string;
  port: number;
  database: string;
  last_synced_at: string | null;
}

export interface TableSummary {
  id: number;
  source_id: number;
  schema_name: string;
  name: string;
  label: string;
}

export interface Column {
  id: number;
  name: string;
  label: string;
  data_type: string;
  type_group: TypeGroup;
  is_primary_key: boolean;
  is_filterable: boolean;
  operators: FilterOperator[];
  is_editable: boolean;
  is_insertable: boolean;
  is_nullable: boolean;
  is_required: boolean;
}

export interface TableMeta extends TableSummary {
  can_update: boolean;
  can_insert: boolean;
  can_delete: boolean;
  read_only_reason: string | null;
  columns: Column[];
}

export interface Filter {
  column: string;
  operator: FilterOperator;
  value?: CellValue | CellValue[];
}

export interface Sort {
  column: string;
  direction: "asc" | "desc";
}

export interface DataQuery {
  columns: string[] | null;
  filters: Filter[];
  sort: Sort[];
  page: number;
  page_size: number;
}

export interface DataPage {
  columns: string[];
  rows: Row[];
  total: number;
  page: number;
  page_size: number;
}

export interface RowUpdate {
  changes: Row;
  original: Row;
}

export interface RowResponse {
  row: Row;
}

export interface TemplateBody {
  schema_version: 1;
  columns: string[] | null;
  filters: Filter[];
  sort: Sort[];
  page_size: number;
}

export interface Template {
  id: number;
  table_id: number;
  name: string;
  description: string | null;
  body: TemplateBody;
  created_at: string;
  updated_at: string;
  problems: string[];
}

export interface TemplateInput {
  table_id: number;
  name: string;
  description: string | null;
  body: TemplateBody;
}

export interface ExportRequest {
  table_id?: number;
  query?: Pick<DataQuery, "columns" | "filters" | "sort">;
  template_id?: number;
}

export interface SyncCounter {
  added: number;
  updated: number;
  deactivated: number;
}

export interface SyncResult {
  source_id: number;
  schema_name: string;
  synced_at: string;
  tables: SyncCounter;
  columns: SyncCounter;
}

export interface SqlStatus {
  enabled: boolean;
  max_rows: number;
  timeout_ms: number;
}

export interface SqlExecuteInput {
  source_id: number;
  sql: string;
  confirm: boolean;
  confirm_without_where: boolean;
  expected_rows: number | null;
}

export interface SqlResult {
  status: "done" | "preview";
  statement_type: string;
  columns: string[];
  rows: CellValue[][];
  truncated: boolean;
  affected_rows: number | null;
  has_where: boolean;
}

export type ChangeAction =
  | "update"
  | "insert"
  | "delete"
  | "sql_select"
  | "sql_preview"
  | "sql_write"
  | "sql_rejected";

export interface ChangeLogEntry {
  id: number;
  created_at: string;
  data_source_id: number | null;
  meta_table_id: number | null;
  action: ChangeAction;
  row_key: Row | null;
  old_values: Row | null;
  new_values: Row | null;
  sql_text: string | null;
  affected_rows: number | null;
  message: string | null;
  client_address: string | null;
}

export interface ChangeLogQuery {
  table_id?: number;
  source_id?: number;
  limit?: number;
  before_id?: number;
}

export interface AdminTable {
  id: number;
  source_id: number;
  schema_name: string;
  name: string;
  label: string | null;
  is_visible: boolean;
  is_active: boolean;
  is_editable: boolean;
  allow_insert: boolean;
  allow_delete: boolean;
  primary_key_problem: string | null;
}

export interface AdminColumn {
  id: number;
  name: string;
  label: string | null;
  data_type: string;
  type_group: TypeGroup;
  position: number;
  is_visible: boolean;
  is_filterable: boolean;
  is_editable: boolean;
  is_primary_key: boolean;
  is_nullable: boolean;
  is_autoincrement: boolean;
  default_value: string | null;
  is_active: boolean;
}

export interface AdminTableDetail extends AdminTable {
  columns: AdminColumn[];
}

export interface AdminColumnInput {
  id: number;
  label: string | null;
  is_visible: boolean;
  is_filterable: boolean;
  is_editable: boolean;
}

export interface AdminTableInput {
  label: string | null;
  is_visible: boolean;
  is_editable: boolean;
  allow_insert: boolean;
  allow_delete: boolean;
  columns: AdminColumnInput[];
}
