import type { CellValue, TypeGroup } from "../types";

/** Значение ячейки для показа. */
export function formatValue(value: CellValue | undefined, group: TypeGroup): string {
  if (value === null || value === undefined) {
    return "NULL";
  }
  if (typeof value === "boolean") {
    return value ? "да" : "нет";
  }
  if (group === "datetime" && typeof value === "string") {
    return value.replace("T", " ");
  }
  return String(value);
}

/** Значение для поля ввода нужного типа. */
export function toInputValue(value: CellValue | undefined, group: TypeGroup): string {
  if (value === null || value === undefined) {
    return "";
  }
  if (group === "datetime" && typeof value === "string") {
    // datetime-local не понимает часовой пояс и доли секунды
    return value.slice(0, 19);
  }
  return String(value);
}

/** Значение из поля ввода в то, что принимает бэкенд: числа и даты — строкой, он сам приведёт их к типу колонки. */
export function fromInputValue(text: string, group: TypeGroup): CellValue {
  if (group === "boolean") {
    return text === "true";
  }
  return text;
}

/** Тип поля ввода по группе типа колонки. */
export function inputType(group: TypeGroup): string {
  if (group === "integer" || group === "number") {
    return "number";
  }
  if (group === "date") {
    return "date";
  }
  if (group === "datetime") {
    return "datetime-local";
  }
  return "text";
}

/** Шаг числового поля: дробные — любые, целые — по одному. */
export function inputStep(group: TypeGroup): string | undefined {
  if (group === "number") {
    return "any";
  }
  if (group === "datetime") {
    return "1";
  }
  return undefined;
}

/** Совпадают ли два значения ячейки. */
export function sameValue(left: CellValue | undefined, right: CellValue | undefined): boolean {
  return (left ?? null) === (right ?? null);
}
