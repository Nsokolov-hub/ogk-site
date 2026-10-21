'use client';

import type { ComponentProps } from 'react';
import { ChevronDown } from 'lucide-react';
import { cn } from '@/lib/cn';
import { describedBy, FieldShell, fieldClasses, useFieldIds, type FieldShellProps } from './Field';

export interface SelectOption {
  value: string;
  label: string;
}

export type SelectProps = FieldShellProps &
  Omit<ComponentProps<'select'>, 'id' | 'className' | 'children'> & {
    options: SelectOption[];
    /** Компактный вид для карточек товара */
    compact?: boolean;
  };

/** Нативный select: лучше всего работает на телефонах и с клавиатурой */
export function Select({ label, error, hint, required, hideLabel, className, id, options, compact, ...rest }: SelectProps) {
  const ids = useFieldIds(id);
  return (
    <FieldShell {...ids} label={label} error={error} hint={hint} required={required} hideLabel={hideLabel} className={className}>
      <div className="relative">
        <select
          id={ids.fieldId}
          aria-invalid={error ? true : undefined}
          aria-describedby={describedBy(error, hint, ids.errorId, ids.hintId)}
          className={cn(
            fieldClasses(!!error),
            'appearance-none pr-10',
            compact && 'h-9 rounded-sm px-3 py-0 text-small md:px-3 md:py-0 md:text-small',
          )}
          {...rest}
        >
          {options.map((o) => (
            <option key={o.value} value={o.value} className="bg-surface-raised text-text">
              {o.label}
            </option>
          ))}
        </select>
        <ChevronDown
          aria-hidden
          size={compact ? 16 : 20}
          strokeWidth={1.5}
          className="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2 text-text-secondary"
        />
      </div>
    </FieldShell>
  );
}
