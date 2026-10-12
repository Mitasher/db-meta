/** Отдаёт браузеру файл на сохранение. */
export function saveBlob(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  // Ссылка нужна браузеру только на время начала скачивания
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
