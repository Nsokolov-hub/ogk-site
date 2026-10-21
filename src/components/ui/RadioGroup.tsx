'use client';

import { useId } from 'react';
import { cn } from '@/lib/cn';

export interface RadioOption<T extends string> {
  value: T;
  label: string;
}

/** Группа радиокнопок на нативных input: стрелки и Tab работают из коробки */
export function RadioGroup<T extends string>({
  legend,
  name,
  value,
  options,
  onChange,
  className,
}: {
  legend: string;
  name: string;
  value: T;
  options: RadioOption<T>[];
  onChange: (value: T) => void;
  className?: string;
}) {
  const uid = useId().replace(/[^a-zA-Z0-9_-]/g, '');
  return (
    <fieldset className={cn('flex flex-col gap-2', className)}>
      <legend className="mb-2 text-small text-text-secondary">{legend}</legend>
      {options.map((o) => {
        const id = `${uid}-${o.value}`;
        return (
          <div key={o.value} className="flex items-center gap-3">
            <input
              id={id}
              type="radio"
              name={name}
              value={o.value}
              checked={value === o.value}
              onChange={() => onChange(o.value)}
              className={cn(
                'size-5 shrink-0 cursor-pointer appearance-none rounded-full border border-text-secondary transition-[border-color,box-shadow] duration-200',
                'hover:border-text checked:border-accent checked:shadow-[inset_0_0_0_4px_var(--color-base),inset_0_0_0_10px_var(--color-accent)]',
              )}
            />
            <label htmlFor={id} className="cursor-pointer text-body text-text">
              {o.label}
            </label>
          </div>
        );
      })}
    </fieldset>
  );
}
