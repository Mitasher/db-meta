import { useCallback, useState } from "react";
import { deleteTemplate, exportExcel, getTables, getTemplates } from "../api";
import { ConfirmDialog } from "../components/Dialog";
import { Notice, type NoticeData } from "../components/Notice";
import { EmptyState, ErrorMessage, Loading } from "../components/StateView";
import type { Template } from "../types";
import { saveBlob } from "../utils/download";
import { tableHref } from "../utils/routing";
import { errorText, useLoad } from "../utils/useLoad";

/** Дата и время для людей. */
function formatDate(value: string): string {
  return new Date(value).toLocaleString("ru-RU", { dateStyle: "short", timeStyle: "short" });
}

/** Экран «Шаблоны»: список, открытие, выгрузка и удаление. */
export function TemplatesPage() {
  const templates = useLoad(getTemplates, []);
  const tables = useLoad(getTables, []);
  const [toDelete, setToDelete] = useState<Template | null>(null);
  const [deleting, setDeleting] = useState(false);
  const [exportingId, setExportingId] = useState<number | null>(null);
  const [notice, setNotice] = useState<NoticeData | null>(null);
  const closeNotice = useCallback(() => setNotice(null), []);
  const tableLabels = new Map((tables.data ?? []).map((table) => [table.id, table.label]));

  const confirmDelete = async () => {
    if (!toDelete) {
      return;
    }
    setDeleting(true);
    try {
      await deleteTemplate(toDelete.id);
      templates.setData((current) => (current ? current.filter((item) => item.id !== toDelete.id) : current));
      setNotice({ kind: "success", text: `Шаблон «${toDelete.name}» удалён` });
    } catch (error) {
      setNotice({ kind: "error", text: `Шаблон не удалён: ${errorText(error)}` });
    } finally {
      setDeleting(false);
      setToDelete(null);
    }
  };

  const download = async (template: Template) => {
    setExportingId(template.id);
    try {
      const file = await exportExcel({ template_id: template.id });
      saveBlob(file.blob, file.filename);
    } catch (error) {
      setNotice({ kind: "error", text: `Выгрузка не удалась: ${errorText(error)}` });
    } finally {
      setExportingId(null);
    }
  };

  return (
    <div className="page">
      <header className="view-header">
        <div>
          <h1 className="view-title">Шаблоны запросов</h1>
          <div className="view-subtitle">Сохраняются на экране таблицы кнопкой «Сохранить как шаблон»</div>
        </div>
      </header>
      <Notice notice={notice} onClose={closeNotice} />
      {templates.loading && !templates.data && <Loading />}
      {templates.error && <ErrorMessage message={templates.error} onRetry={templates.reload} />}
      {templates.data && templates.data.length === 0 && <EmptyState text="Шаблонов пока нет" />}
      <div className="cards">
        {(templates.data ?? []).map((template) => (
          <article key={template.id} className={template.problems.length ? "card card-warning" : "card"}>
            <div className="card-head">
              <h2 className="card-title">{template.name}</h2>
              <span className="badge badge-muted">{tableLabels.get(template.table_id) ?? `таблица #${template.table_id}`}</span>
            </div>
            {template.description && <p className="card-text">{template.description}</p>}
            <div className="card-meta">
              Условий: {template.body.filters.length}
              {template.body.sort.length > 0 && " · с сортировкой"}
              {template.body.columns && ` · колонок: ${template.body.columns.length}`} · изменён{" "}
              {formatDate(template.updated_at)}
            </div>
            {template.problems.map((problem) => (
              <div key={problem} className="form-error">
                {problem}
              </div>
            ))}
            <div className="card-actions">
              <a className="button button-small button-primary" href={tableHref(template.table_id, template.id)}>
                Открыть
              </a>
              <button
                type="button"
                className="button button-small"
                onClick={() => download(template)}
                disabled={exportingId === template.id || template.problems.length > 0}
              >
                {exportingId === template.id ? "Готовим файл…" : "Скачать Excel"}
              </button>
              <button type="button" className="button button-small button-ghost-danger" onClick={() => setToDelete(template)}>
                Удалить
              </button>
            </div>
          </article>
        ))}
      </div>
      {toDelete && (
        <ConfirmDialog
          title="Удалить шаблон?"
          confirmText="Удалить"
          danger
          busy={deleting}
          onConfirm={confirmDelete}
          onCancel={() => setToDelete(null)}
        >
          Шаблон «{toDelete.name}» будет удалён. Данные таблицы это не затронет.
        </ConfirmDialog>
      )}
    </div>
  );
}
