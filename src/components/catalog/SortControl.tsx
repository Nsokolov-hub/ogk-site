'use client';

import { ChevronDown } from 'lucide-react';
import { useLocale, useTranslations } from 'next-intl';
import type { CatalogSort, FacetKey } from '@/types/catalog';
import { useFieldIds } from '@/components/ui/Field';
import { catalogHref, type CatalogQuery } from '@/lib/catalog';
import { localizedPath, useCatalogNavigate } from '@/lib/catalog-nav';

const SORTS: CatalogSort[] = ['popular', 'name', 'availability'];

/** «Сортировать по»: популярности (по умолчанию, в наличии выше), названию A–Z, наличию */
export function SortControl({ basePath, query }: { basePath: string; query: CatalogQuery }) {
  const t = useTranslations('catalog');
  const locale = useLocale();
  const navigate = useCatalogNavigate();
  const { fieldId } = useFieldIds();

  return (
    <form method="get" action={localizedPath(locale, basePath)} className="flex items-center gap-2">
      {(Object.entries(query.filters) as [FacetKey, string[]][]).flatMap(([key, values]) =>
        values.map((v) => <input key={`${key}-${v}`} type="hidden" name={key} value={v} />),
      )}
      <label htmlFor={fieldId} className="whitespace-nowrap text-small text-text-secondary">
        {t('sortLabel')}
      </label>
      <div className="relative">
        <select
          id={fieldId}
          name="sort"
          defaultValue={query.sort}
          onChange={(e) => navigate(catalogHref(basePath, { filters: query.filters, sort: e.target.value as CatalogSort }))}
          className="h-10 cursor-pointer appearance-none rounded-pill border border-border bg-surface py-0 pl-4 pr-10 text-small text-text outline-offset-0 transition-colors hover:border-text-secondary"
        >
          {SORTS.map((s) => (
            <option key={s} value={s} className="bg-surface-raised">
              {t(`sort.${s}`)}
            </option>
          ))}
        </select>
        <ChevronDown aria-hidden size={16} strokeWidth={1.5} className="pointer-events-none absolute right-3.5 top-1/2 -translate-y-1/2 text-text-secondary" />
      </div>
      <noscript>
        <button type="submit" className="h-10 rounded-pill bg-accent px-4 text-small font-medium text-text-on-accent">
          {t('sortApply')}
        </button>
      </noscript>
    </form>
  );
}
