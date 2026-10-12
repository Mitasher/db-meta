import type { KeyboardEvent, Ref } from "react";
import type { TypeGroup } from "../types";
import { inputStep, inputType } from "../utils/values";

interface ValueInputProps {
  group: TypeGroup;
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
  className?: string;
  autoFocus?: boolean;
  inputRef?: Ref<HTMLInputElement & HTMLSelectElement>;
  onKeyDown?: (event: KeyboardEvent<HTMLInputElement | HTMLSelectElement>) => void;
  onBlur?: () => void;
  emptyOption?: string;
  ariaLabel?: string;
}

/** Поле ввода по типу колонки: текст, число, дата, дата-время или да/нет. */
export function ValueInput({
  group,
  value,
  onChange,
  placeholder,
  className = "input",
  autoFocus,
  inputRef,
  onKeyDown,
  onBlur,
  emptyOption,
  ariaLabel,
}: ValueInputProps) {
  if (group === "boolean") {
    return (
      <select
        ref={inputRef}
        className={className}
        value={value}
        autoFocus={autoFocus}
        onChange={(event) => onChange(event.target.value)}
        onKeyDown={onKeyDown}
        onBlur={onBlur}
        aria-label={ariaLabel}
      >
        {emptyOption !== undefined && <option value="">{emptyOption}</option>}
        <option value="true">да</option>
        <option value="false">нет</option>
      </select>
    );
  }
  return (
    <input
      ref={inputRef}
      className={className}
      type={inputType(group)}
      step={inputStep(group)}
      value={value}
      placeholder={placeholder}
      autoFocus={autoFocus}
      onChange={(event) => onChange(event.target.value)}
      onKeyDown={onKeyDown}
      onBlur={onBlur}
      aria-label={ariaLabel}
    />
  );
}
