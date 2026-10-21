import { ChevronRight, House } from 'lucide-react';
import { useTranslations } from 'next-intl';
import type { BreadcrumbItem } from '@/types/content';
import { Link } from '@/i18n/navigation';
import { cn } from '@/lib/cn';

/** Хлебные крошки (ТЗ 11.4): на всех страницах, кроме главной; последнее звено — без ссылки */
export function Breadcrumbs({ items, className }: { items: BreadcrumbItem[]; className?: string }) {
  const t = useTranslations('catalog');
  return (
    <nav aria-label={t('breadcrumbs')} className={cn('text-small', className)}>
      <ol className="flex flex-wrap items-center gap-x-1.5 gap-y-1 text-text-secondary">
        {items.map((item, i) => {
          const last = i === items.length - 1;
          return (
            <li key={`${item.label}-${i}`} className="inline-flex items-center gap-1.5">
              {i > 0 ? <ChevronRight aria-hidden size={14} strokeWidth={1.5} className="shrink-0 opacity-60" /> : null}
              {item.href && !last ? (
                <Link href={item.href} className="inline-flex items-center gap-1.5 transition-colors hover:text-accent">
                  {i === 0 ? <House aria-hidden size={15} strokeWidth={1.5} /> : null}
                  {item.label}
                </Link>
              ) : (
                <span aria-current={last ? 'page' : undefined} className={cn(last && 'text-text')}>
                  {item.label}
                </span>
              )}
            </li>
          );
        })}
      </ol>
    </nav>
  );
}
