'use client';

import type { ComponentProps } from 'react';
import { cn } from '@/lib/cn';
import { describedBy, FieldShell, fieldClasses, useFieldIds, type FieldShellProps } from './Field';

export type TextareaProps = FieldShellProps & Omit<ComponentProps<'textarea'>, 'id' | 'className'>;

export function Textarea({ label, error, hint, required, hideLabel, className, id, rows = 5, ...rest }: TextareaProps) {
  const ids = useFieldIds(id);
  return (
    <FieldShell {...ids} label={label} error={error} hint={hint} required={required} hideLabel={hideLabel} className={className}>
      <textarea
        id={ids.fieldId}
        rows={rows}
        aria-invalid={error ? true : undefined}
        aria-required={required || undefined}
        aria-describedby={describedBy(error, hint, ids.errorId, ids.hintId)}
        className={cn(fieldClasses(!!error), 'min-h-32 resize-y')}
        {...rest}
      />
    </FieldShell>
  );
}
