import { ChevronDown } from 'lucide-react';
import type { Faq } from '@/types/content';
import { cn } from '@/lib/cn';

/**
 * Частые вопросы: нативные details/summary — работают без JS, ответы есть в HTML.
 * Разметка FAQPage ставится только там, где этот блок виден (SEO-06).
 */
export function FaqSection({ id, title, items, className }: { id: string; title: string; items: Faq[]; className?: string }) {
  if (!items.length) return null;
  return (
    <section aria-labelledby={id} className={cn('max-w-[960px]', className)}>
      <h2 id={id} className="text-h3 font-medium text-text">
        {title}
      </h2>
      <div className="mt-6 flex flex-col gap-3">
        {items.map((f) => (
          <details key={f.q} className="group rounded-field bg-surface px-5 md:px-6">
            <summary className="flex cursor-pointer list-none items-center justify-between gap-4 py-4 text-body font-medium text-text md:text-lg [&::-webkit-details-marker]:hidden">
              {f.q}
              <ChevronDown aria-hidden size={20} strokeWidth={1.5} className="shrink-0 text-accent transition-transform group-open:rotate-180" />
            </summary>
            <p className="pb-5 text-body text-text-secondary">{f.a}</p>
          </details>
        ))}
      </div>
    </section>
  );
}
