'use client';

import { useState } from 'react';
import * as RD from '@radix-ui/react-dialog';
import { SlidersHorizontal, X } from 'lucide-react';
import { useTranslations } from 'next-intl';
import type { Facet } from '@/types/catalog';
import type { CategoryPageData } from '@/types/content';
import { countSelected, type CatalogQuery } from '@/lib/catalog';
import { cn } from '@/lib/cn';
import { CatalogFilters } from './CatalogFilters';
import { CategoryNav } from './CategoryNav';

/** На телефоне и планшете фильтры выезжают снизу (ТЗ 5.5) */
export function MobileFilters({
  facets,
  basePath,
  query,
  nav,
  className,
}: {
  facets: Facet[];
  basePath: string;
  query: CatalogQuery;
  nav: CategoryPageData['nav'];
  className?: string;
}) {
  const t = useTranslations('catalog');
  const tc = useTranslations('common');
  const [open, setOpen] = useState(false);
  const selected = countSelected(query.filters);

  return (
    <RD.Root open={open} onOpenChange={setOpen}>
      <RD.Trigger
        className={cn(
          'inline-flex h-10 items-center gap-2 rounded-pill border border-accent px-4 text-small font-medium text-accent transition-colors hover:bg-accent hover:text-text-on-accent',
          className,
        )}
      >
        <SlidersHorizontal aria-hidden size={18} strokeWidth={1.5} />
        {t('filters')}
        {selected ? (
          <span className="grid h-5 min-w-5 place-items-center rounded-pill bg-accent px-1.5 text-[11px] font-semibold text-text-on-accent">{selected}</span>
        ) : null}
      </RD.Trigger>
      <RD.Portal>
        <RD.Overlay className="fixed inset-0 z-[150] bg-base-deep/70 data-[state=open]:animate-fade-in" />
        <RD.Content
          aria-describedby={undefined}
          className="fixed inset-x-0 bottom-0 z-[151] flex max-h-[90svh] flex-col rounded-t-block bg-base data-[state=open]:animate-sheet-up"
        >
          <div className="flex items-center justify-between border-b border-border px-5 py-3">
            <RD.Title className="text-h4 font-medium">{t('filters')}</RD.Title>
            <RD.Close aria-label={tc('close')} className="grid size-11 place-items-center rounded-full text-text-secondary hover:text-text">
              <X aria-hidden size={22} strokeWidth={1.5} />
            </RD.Close>
          </div>
          <div className="overflow-y-auto overscroll-contain px-5">
            <CategoryNav nav={nav} className="pt-3" />
            <CatalogFilters facets={facets} basePath={basePath} query={query} onDone={() => setOpen(false)} />
          </div>
        </RD.Content>
      </RD.Portal>
    </RD.Root>
  );
}
