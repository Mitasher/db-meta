interface ErrorMessageProps {
  message: string;
  onRetry?: () => void;
}

/** Индикатор загрузки. */
export function Loading({ text = "Загрузка…" }: { text?: string }) {
  return (
    <div className="state state-loading" role="status">
      <span className="spinner" aria-hidden="true" />
      {text}
    </div>
  );
}

/** Пустой результат. */
export function EmptyState({ text }: { text: string }) {
  return <div className="state state-empty">{text}</div>;
}

/** Ошибка от бэкенда с кнопкой повтора. */
export function ErrorMessage({ message, onRetry }: ErrorMessageProps) {
  return (
    <div className="state state-error" role="alert">
      <span>{message}</span>
      {onRetry && (
        <button type="button" className="button button-small" onClick={onRetry}>
          Повторить
        </button>
      )}
    </div>
  );
}
