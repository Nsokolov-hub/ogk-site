'use client';

import { prefillRequest } from '@/components/forms/RequestForm';
import { cn } from '@/lib/cn';

/** «Запросить образец» — дописывает строку в форму заявки на странице и прокручивает к ней */
export function RequestDocButton({ label, text, className }: { label: string; text: string; className?: string }) {
  return (
    <button
      type="button"
      onClick={() => prefillRequest(text)}
      className={cn(
        'inline-flex h-10 shrink-0 items-center rounded-pill bg-surface-strong px-4 text-small font-medium text-accent transition-colors hover:text-accent-hover',
        className,
      )}
    >
      {label}
    </button>
  );
}
