'use client';

import type { ComponentProps, ReactNode } from 'react';
import { Check } from 'lucide-react';
import { cn } from '@/lib/cn';
import { useFieldIds } from './Field';

export type CheckboxProps = Omit<ComponentProps<'input'>, 'type' | 'id' | 'className'> & {
  label: ReactNode;
  error?: string;
  id?: string;
  className?: string;
};

/** Квадрат 20 px, отмечен — заливка accent. Ссылки в подписи не переключают галочку. */
export function Checkbox({ label, error, id, className, required, ...rest }: CheckboxProps) {
  const { fieldId, errorId } = useFieldIds(id);
  return (
    <div className={cn('flex flex-col gap-1.5', className)}>
      <div className="flex items-start gap-3">
        <span className="relative mt-0.5 inline-grid size-5 shrink-0 place-items-center">
          <input
            id={fieldId}
            type="checkbox"
            aria-invalid={error ? true : undefined}
            aria-required={required || undefined}
            aria-describedby={error ? errorId : undefined}
            className={cn(
              'peer size-5 cursor-pointer appearance-none rounded-[6px] border bg-transparent transition-colors duration-200',
              'checked:border-accent checked:bg-accent',
              error ? 'border-error' : 'border-text-secondary hover:border-text',
            )}
            {...rest}
          />
          <Check
            aria-hidden
            size={14}
            strokeWidth={3}
            className="pointer-events-none absolute text-base opacity-0 transition-opacity peer-checked:opacity-100"
          />
        </span>
        <label htmlFor={fieldId} className="cursor-pointer text-small text-text [&_a]:text-accent [&_a]:underline-offset-2 [&_a:hover]:underline">
          {label}
          {required ? (
            <span aria-hidden className="text-accent">
              {' '}
              *
            </span>
          ) : null}
        </label>
      </div>
      {error ? (
        <p id={errorId} className="pl-8 text-small text-error">
          {error}
        </p>
      ) : null}
    </div>
  );
}
