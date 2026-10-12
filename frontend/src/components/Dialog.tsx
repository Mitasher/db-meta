import { useEffect, type ReactNode } from "react";

interface DialogProps {
  title: string;
  children: ReactNode;
  footer: ReactNode;
  onClose: () => void;
}

interface ConfirmDialogProps {
  title: string;
  children: ReactNode;
  confirmText: string;
  danger?: boolean;
  busy?: boolean;
  confirmDisabled?: boolean;
  onConfirm: () => void;
  onCancel: () => void;
}

/** Модальное окно; Escape и клик по фону закрывают его. */
export function Dialog({ title, children, footer, onClose }: DialogProps) {
  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        onClose();
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  return (
    <div className="dialog-backdrop" onMouseDown={(event) => event.target === event.currentTarget && onClose()}>
      <div className="dialog" role="dialog" aria-modal="true" aria-label={title}>
        <h2 className="dialog-title">{title}</h2>
        <div className="dialog-body">{children}</div>
        <div className="dialog-footer">{footer}</div>
      </div>
    </div>
  );
}

/** Окно подтверждения действия. */
export function ConfirmDialog({
  title,
  children,
  confirmText,
  danger = false,
  busy = false,
  confirmDisabled = false,
  onConfirm,
  onCancel,
}: ConfirmDialogProps) {
  return (
    <Dialog
      title={title}
      onClose={onCancel}
      footer={
        <>
          <button type="button" className="button" onClick={onCancel} disabled={busy}>
            Отмена
          </button>
          <button
            type="button"
            className={danger ? "button button-danger" : "button button-primary"}
            onClick={onConfirm}
            disabled={busy || confirmDisabled}
          >
            {busy ? "Выполняется…" : confirmText}
          </button>
        </>
      }
    >
      {children}
    </Dialog>
  );
}
