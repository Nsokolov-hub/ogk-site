'use client';

import { useId, useState } from 'react';
import { Minus, Plus } from 'lucide-react';
import { cn } from '@/lib/cn';

/** Количество: кнопки −/+ и ввод с клавиатуры, значение в пределах min…max */
export function QuantityStepper({
  label,
  value,
  onChange,
  min = 1,
  max = 999,
  decreaseLabel,
  increaseLabel,
  className,
}: {
  label: string;
  value: number;
  onChange: (value: number) => void;
  min?: number;
  max?: number;
  decreaseLabel: string;
  increaseLabel: string;
  className?: string;
}) {
  const uid = useId().replace(/[^a-zA-Z0-9_-]/g, '');
  const [draft, setDraft] = useState<string | null>(null);
  const clamp = (n: number) => Math.min(max, Math.max(min, n));

  const commit = () => {
    if (draft === null) return;
    const n = Number.parseInt(draft, 10);
    onChange(Number.isFinite(n) ? clamp(n) : value);
    setDraft(null);
  };

  const btn =
    'grid size-11 place-items-center rounded-full text-text transition-colors hover:text-accent disabled:pointer-events-none disabled:opacity-30';

  return (
    <div className={cn('flex flex-col gap-1.5', className)}>
      <label htmlFor={`${uid}-input`} className="text-small text-text-secondary">
        {label}
      </label>
      <div className="inline-flex h-12 w-fit items-center rounded-pill bg-surface-strong px-0.5">
        <button type="button" className={btn} aria-label={decreaseLabel} disabled={value <= min} onClick={() => onChange(clamp(value - 1))}>
          <Minus aria-hidden size={18} strokeWidth={1.5} />
        </button>
        <input
          id={`${uid}-input`}
          inputMode="numeric"
          pattern="[0-9]*"
          autoComplete="off"
          value={draft ?? String(value)}
          onChange={(e) => setDraft(e.target.value.replace(/\D/g, '').slice(0, 3))}
          onBlur={commit}
          onKeyDown={(e) => {
            if (e.key === 'Enter') {
              e.preventDefault();
              commit();
            }
          }}
          className="w-12 bg-transparent text-center text-lg tabular-nums text-text outline-offset-0"
        />
        <button type="button" className={btn} aria-label={increaseLabel} disabled={value >= max} onClick={() => onChange(clamp(value + 1))}>
          <Plus aria-hidden size={18} strokeWidth={1.5} />
        </button>
      </div>
    </div>
  );
}
