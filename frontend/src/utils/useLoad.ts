import { useCallback, useEffect, useRef, useState, type DependencyList } from "react";

export interface LoadState<T> {
  data: T | null;
  error: string | null;
  loading: boolean;
  reload: () => void;
  setData: (update: (current: T | null) => T | null) => void;
}

/** Текст ошибки любого вида. */
export function errorText(error: unknown): string {
  return error instanceof Error ? error.message : String(error);
}

/** Загружает данные при смене зависимостей; ответ устаревшего запроса отбрасывается. */
export function useLoad<T>(load: () => Promise<T>, deps: DependencyList): LoadState<T> {
  const [data, setDataState] = useState<T | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [attempt, setAttempt] = useState(0);
  const requestId = useRef(0);

  useEffect(() => {
    const current = ++requestId.current;
    setLoading(true);
    setError(null);
    load()
      .then((result) => {
        if (current === requestId.current) {
          setDataState(result);
        }
      })
      .catch((reason: unknown) => {
        if (current === requestId.current) {
          setError(errorText(reason));
        }
      })
      .finally(() => {
        if (current === requestId.current) {
          setLoading(false);
        }
      });
    // load меняется на каждом рендере — перезапуск идёт только по deps и reload
  }, [...deps, attempt]);

  const reload = useCallback(() => setAttempt((value) => value + 1), []);
  const setData = useCallback((update: (current: T | null) => T | null) => setDataState(update), []);
  return { data, error, loading, reload, setData };
}
