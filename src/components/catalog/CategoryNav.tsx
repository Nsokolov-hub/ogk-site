import { ArrowLeft, ChevronDown } from 'lucide-react';
import { useTranslations } from 'next-intl';
import type { CategoryPageData } from '@/types/content';
import { Link } from '@/i18n/navigation';
import { cn } from '@/lib/cn';

/** Блок «Категории» боковой панели: раскрывающийся список разделов (ТЗ 11.2, PDF «Каталог») */
export function CategoryNav({ nav, className }: { nav: CategoryPageData['nav']; className?: string }) {
  const t = useTranslations('catalog');
  return (
    <nav aria-label={t('categories')} className={cn('pb-2', className)}>
      <details open className="group">
        <summary className="flex cursor-pointer list-none items-center justify-between gap-3 py-2 text-body font-medium text-text [&::-webkit-details-marker]:hidden">
          {nav.title}
          <ChevronDown aria-hidden size={18} strokeWidth={1.5} className="shrink-0 text-text-secondary transition-transform group-open:rotate-180" />
        </summary>
        {nav.parent ? (
          <Link
            href={nav.parent.href}
            className="mt-1 inline-flex items-center gap-2 py-1.5 text-small text-text-secondary transition-colors hover:text-accent"
          >
            <ArrowLeft aria-hidden size={14} strokeWidth={1.5} />
            {nav.parent.label}
          </Link>
        ) : null}
        <ul className="mt-1 flex flex-col">
          {nav.items.map((item) => (
            <li key={item.href}>
              <Link
                href={item.href}
                aria-current={item.active ? 'page' : undefined}
                className={cn(
                  'block rounded-sm px-3 py-2 text-small transition-colors',
                  item.active ? 'bg-surface-strong font-medium text-accent' : 'text-text hover:text-accent',
                )}
              >
                {item.label}
              </Link>
            </li>
          ))}
        </ul>
      </details>
    </nav>
  );
}
