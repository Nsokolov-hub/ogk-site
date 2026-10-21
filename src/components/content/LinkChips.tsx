import type { LinkItem } from '@/types/content';
import { Chip } from '@/components/ui/Chip';
import { cn } from '@/lib/cn';

/** Внутренние ссылки «Смотрите также» (SEO-08) */
export function LinkChips({ id, title, items, className }: { id: string; title: string; items: LinkItem[]; className?: string }) {
  if (!items.length) return null;
  return (
    <section aria-labelledby={id} className={className}>
      <h2 id={id} className="text-h3 font-medium text-text">
        {title}
      </h2>
      <ul className={cn('mt-6 flex flex-wrap gap-2')}>
        {items.map((r) => (
          <li key={`${r.href}-${r.label}`}>
            <Chip label={r.label} href={r.href} />
          </li>
        ))}
      </ul>
    </section>
  );
}
