import { useEffect, type ReactNode } from "react";

export interface NoticeData {
  kind: "success" | "error" | "info";
  text: string;
}

interface NoticeProps {
  notice: NoticeData | null;
  onClose: () => void;
  action?: ReactNode;
}

/** Сообщение над данными; об успехе само скрывается через несколько секунд. */
export function Notice({ notice, onClose, action }: NoticeProps) {
  useEffect(() => {
    if (notice?.kind !== "success") {
      return;
    }
    const timer = setTimeout(onClose, 4000);
    return () => clearTimeout(timer);
  }, [notice, onClose]);

  if (!notice) {
    return null;
  }
  return (
    <div className={`notice notice-${notice.kind}`} role={notice.kind === "error" ? "alert" : "status"}>
      <span className="notice-text">{notice.text}</span>
      {action}
      <button type="button" className="button button-icon" onClick={onClose} title="Закрыть">
        ×
      </button>
    </div>
  );
}
