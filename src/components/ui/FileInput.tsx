'use client';

import { useRef } from 'react';
import { Paperclip, X } from 'lucide-react';
import { cn } from '@/lib/cn';
import { useFieldIds } from './Field';

function formatSize(bytes: number) {
  if (bytes < 1024) return `${bytes} Б`;
  if (bytes < 1024 * 1024) return `${Math.round(bytes / 1024)} КБ`;
  return `${(bytes / 1024 / 1024).toFixed(1).replace('.', ',')} МБ`;
}

/** Один файл: кнопка выбора, имя и размер выбранного файла, «Убрать» */
export function FileInput({
  label,
  hint,
  removeLabel,
  accept,
  file,
  error,
  onChange,
  className,
}: {
  label: string;
  hint?: string;
  removeLabel: string;
  accept: string;
  file: File | undefined;
  error?: string;
  onChange: (file: File | undefined) => void;
  className?: string;
}) {
  const { fieldId, errorId, hintId } = useFieldIds();
  const inputRef = useRef<HTMLInputElement>(null);

  return (
    <div className={cn('flex flex-col gap-1.5', className)}>
      <div className="flex flex-wrap items-center gap-3">
        <input
          ref={inputRef}
          id={fieldId}
          type="file"
          accept={accept}
          className="peer sr-only"
          aria-invalid={error ? true : undefined}
          aria-describedby={error ? errorId : hint ? hintId : undefined}
          onChange={(e) => {
            onChange(e.target.files?.[0]);
            e.target.value = '';
          }}
        />
        <label
          htmlFor={fieldId}
          className={cn(
            'inline-flex h-11 cursor-pointer items-center gap-2 rounded-pill border border-dashed px-5 text-small font-medium text-accent transition-colors',
            'hover:border-accent peer-focus-visible:outline-2 peer-focus-visible:outline-offset-2 peer-focus-visible:outline-accent',
            error ? 'border-error' : 'border-border',
          )}
        >
          <Paperclip aria-hidden size={18} strokeWidth={1.5} />
          {label}
        </label>
        {file ? (
          <span className="inline-flex max-w-full items-center gap-2 rounded-pill bg-surface-strong py-1.5 pl-4 pr-1.5 text-small text-text">
            <span className="truncate">{file.name}</span>
            <span className="shrink-0 text-text-secondary">{formatSize(file.size)}</span>
            <button
              type="button"
              aria-label={`${removeLabel}: ${file.name}`}
              onClick={() => {
                onChange(undefined);
                inputRef.current?.focus();
              }}
              className="grid size-8 place-items-center rounded-full text-text-secondary hover:text-error"
            >
              <X aria-hidden size={16} />
            </button>
          </span>
        ) : null}
      </div>
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
