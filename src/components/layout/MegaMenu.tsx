'use client';

import { useState } from 'react';
import { ArrowRight, ChevronRight } from 'lucide-react';
import { useTranslations } from 'next-intl';
import type { Category } from '@/types/catalog';
import { Link } from '@/i18n/navigation';
import { cn } from '@/lib/cn';

/** Мегаменю «Каталог»: слева разделы, справа подразделы наведённого или сфокусированного раздела */
export function MegaMenu({ id, tree, onNavigate }: { id: string; tree: Category[]; onNavigate: () => void }) {
  const t = useTranslations('megaMenu');
  const [active, setActive] = useState(0);
  const current = tree[active];

  return (
    <div
      id={id}
      className="absolute inset-x-0 top-full mt-2 animate-fade-in rounded-block border border-border bg-surface-raised p-6 shadow-[0_24px_80px_rgb(0_0_0/0.45)] xl:p-8"
    >
      <div className="grid grid-cols-[minmax(280px,380px)_1fr] gap-8">
        <ul aria-label={t('title')} className="flex flex-col gap-1 border-r border-border pr-6">
          {tree.map((c, i) => (
            <li key={c.slug}>
              <Link
                href={c.href}
                onMouseEnter={() => setActive(i)}
                onFocus={() => setActive(i)}
                onClick={onNavigate}
                className={cn(
                  'flex items-center justify-between gap-3 rounded-sm px-4 py-2.5 text-body font-medium transition-colors',
                  i === active ? 'bg-surface-strong text-accent' : 'text-text hover:text-accent',
                )}
              >
                {c.name}
                {c.children?.length ? <ChevronRight aria-hidden size={18} strokeWidth={1.5} className="shrink-0" /> : null}
              </Link>
            </li>
          ))}
        </ul>

        <div className="flex flex-col py-1">
          <p className="text-h4 font-medium text-text">{current.name}</p>
          {current.children?.length ? (
            <ul className="mt-5 grid grid-cols-2 gap-x-6 gap-y-1 xl:grid-cols-3">
              {current.children.map((sub) => (
                <li key={sub.slug}>
                  <Link href={sub.href} onClick={onNavigate} className="block rounded-sm py-2 text-body text-text-secondary transition-colors hover:text-accent">
                    {sub.name}
                  </Link>
                </li>
              ))}
            </ul>
          ) : null}
          <Link
            href={current.href}
            onClick={onNavigate}
            className="mt-6 inline-flex w-fit items-center gap-2 text-body font-medium text-accent transition-colors hover:text-accent-hover"
          >
            {t('allInSection')}
            <ArrowRight aria-hidden size={18} strokeWidth={1.5} />
          </Link>
        </div>
      </div>

      <div className="mt-6 border-t border-border pt-5">
        <Link
          href="/catalog/"
          onClick={onNavigate}
          className="inline-flex items-center gap-2 text-body font-medium text-text transition-colors hover:text-accent"
        >
          {t('allCatalog')}
          <ArrowRight aria-hidden size={18} strokeWidth={1.5} />
        </Link>
      </div>
    </div>
  );
}
