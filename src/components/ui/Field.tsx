'use client';

import { useId, type ReactNode } from 'react';
import { cn } from '@/lib/cn';

/** Общий вид полей ввода: фон surface-strong, скругление 16, рамка появляется на hover/focus */
export function fieldClasses(invalid?: boolean, className?: string) {
  return cn(
    'ym-disable-keys w-full rounded-field border bg-surface-strong px-4 py-3 text-body text-text md:px-[22px] md:py-[14px] md:text-lg',
    'placeholder:text-text-placeholder transition-colors duration-300 outline-offset-0',
    'hover:border-border focus-visible:border-border-strong',
    invalid ? 'border-error hover:border-error' : 'border-transparent',
    className,
  );
}

export interface FieldShellProps {
  label: ReactNode;
  error?: string;
  hint?: string;
  required?: boolean;
  /** Спрятать подпись визуально (останется для скринридеров) */
  hideLabel?: boolean;
  className?: string;
  id?: string;
}

/** Подпись + поле + подсказка/ошибка с правильными связями aria-describedby */
export function useFieldIds(id?: string) {
  const auto = useId();
  const fieldId = id ?? `f${auto.replace(/[^a-zA-Z0-9_-]/g, '')}`;
  return { fieldId, errorId: `${fieldId}-error`, hintId: `${fieldId}-hint` };
}

export function FieldShell({
  label,
  error,
  hint,
  required,
  hideLabel,
  className,
  fieldId,
  errorId,
  hintId,
  children,
}: FieldShellProps & { fieldId: string; errorId: string; hintId: string; children: ReactNode }) {
  return (
    <div className={cn('flex flex-col gap-1.5', className)}>
      <label htmlFor={fieldId} className={cn('text-small text-text-secondary', hideLabel && 'sr-only')}>
        {label}
        {required ? (
          <span aria-hidden className="text-accent">
            {' '}
            *
          </span>
        ) : null}
      </label>
      {children}
      {hint && !error ? (
        <p id={hintId} className="text-caption text-text-secondary">
          {hint}
        </p>
      ) : null}
      {error ? (
        <p id={errorId} className="text-small text-error">
          {error}
        </p>
      ) : null}
    </div>
  );
}

export function describedBy(error: string | undefined, hint: string | undefined, errorId: string, hintId: string) {
  if (error) return errorId;
  if (hint) return hintId;
  return undefined;
}
