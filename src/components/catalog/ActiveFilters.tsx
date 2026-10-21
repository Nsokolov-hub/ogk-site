import { X } from 'lucide-react';
import { useTranslations } from 'next-intl';
import type { Facet, FacetKey } from '@/types/catalog';
import { Link } from '@/i18n/navigation';
import { catalogHref, countSelected, withoutValue, type CatalogQuery } from '@/lib/catalog';
import { facetValueLabel } from './facet-label';

const QUALIFIED: FacetKey[] = ['pack', 'phase', 'length', 'diameter', 'particle', 'ph'];

/** Выбранные значения чипами над сеткой (ТЗ 5.5). Каждый чип — ссылка без этого значения. */
export function ActiveFilters({ facets, basePath, query }: { facets: Facet[]; basePath: string; query: CatalogQuery }) {
  const t = useTranslations('catalog');
  if (!countSelected(query.filters)) return null;

  const chips = facets.flatMap((f) =>
    f.values
      .filter((v) => v.selected)
      .map((v) => {
        // У числовых и технических значений («5», «C18») добавляем название фильтра, иначе чип непонятен
        const value = facetValueLabel(t, f.key, v);
        const label = QUALIFIED.includes(f.key) ? `${t(`facets.${f.key}`)}: ${value}` : value;
        return {
          id: `${f.key}-${v.value}`,
          label,
          href: catalogHref(basePath, { filters: withoutValue(query.filters, f.key, v.value), sort: query.sort }),
        };
      }),
  );

  return (
    <ul className="flex flex-wrap items-center gap-2">
      {chips.map((c) => (
        <li key={c.id}>
          <Link
            href={c.href}
            scroll={false}
            aria-label={t('removeFilter', { label: c.label })}
            className="inline-flex h-8 items-center gap-1.5 rounded-pill bg-surface-strong pl-3 pr-2 text-small text-text transition-colors hover:text-accent"
          >
            {c.label}
            <X aria-hidden size={14} strokeWidth={2} />
          </Link>
        </li>
      ))}
      <li>
        <Link href={catalogHref(basePath, { sort: query.sort })} scroll={false} className="px-2 text-small font-medium text-accent hover:text-accent-hover">
          {t('resetAll')}
        </Link>
      </li>
    </ul>
  );
}
