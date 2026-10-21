'use client';

import type { ComponentProps } from 'react';
import { describedBy, FieldShell, fieldClasses, useFieldIds, type FieldShellProps } from './Field';

export type InputProps = FieldShellProps & Omit<ComponentProps<'input'>, 'id' | 'className'> & { inputClassName?: string };

export function Input({ label, error, hint, required, hideLabel, className, id, inputClassName, ...rest }: InputProps) {
  const ids = useFieldIds(id);
  return (
    <FieldShell {...ids} label={label} error={error} hint={hint} required={required} hideLabel={hideLabel} className={className}>
      <input
        id={ids.fieldId}
        aria-invalid={error ? true : undefined}
        aria-required={required || undefined}
        aria-describedby={describedBy(error, hint, ids.errorId, ids.hintId)}
        className={fieldClasses(!!error, inputClassName)}
        {...rest}
      />
    </FieldShell>
  );
}
