'use client';

import { useState } from 'react';
import { Check, ChevronDown, Search } from 'lucide-react';
import { useLocale, useTranslations } from 'next-intl';
import type { CatalogFilters as Filters, Facet, FacetKey } from '@/types/catalog';
import { Button } from '@/components/ui/Button';
import { useFieldIds } from '@/components/ui/Field';
import { catalogHref, countSelected, type CatalogQuery } from '@/lib/catalog';
import { localizedPath, useCatalogNavigate } from '@/lib/catalog-nav';
import { cn } from '@/lib/cn';
import { facetValueLabel } from './facet-label';

const VISIBLE = 10;
const SEARCH_FROM = 15;

/**
 * Фильтры (ТЗ 5.5): счётчик у каждого значения, 10 строк + «Показать больше», поиск по значениям,
 * «Применить» и «Сбросить». Это обычная GET-форма — работает и без JS.
 */
export function CatalogFilters({
  facets,
  basePath,
  query,
  onDone,
  className,
}: {
  facets: Facet[];
  basePath: string;
  query: CatalogQuery;
  /** Закрыть мобильную панель после применения */
  onDone?: () => void;
  className?: string;
}) {
  const t = useTranslations('catalog');
  const locale = useLocale();
  const navigate = useCatalogNavigate();
  const [draft, setDraft] = useState<Filters>(query.filters);
  const resetHref = catalogHref(basePath, { sort: query.sort });

  const toggle = (key: FacetKey, value: string) =>
    setDraft((d) => {
      const cur = d[key] ?? [];
      const nextValues = cur.includes(value) ? cur.filter((v) => v !== value) : [...cur, value];
      const next = { ...d, [key]: nextValues };
      if (!nextValues.length) delete next[key];
      return next;
    });

  if (!facets.length) return null;

  return (
    <form
      method="get"
      action={localizedPath(locale, basePath)}
      onSubmit={(e) => {
        e.preventDefault();
        navigate(catalogHref(basePath, { filters: draft, sort: query.sort }));
        onDone?.();
      }}
      className={cn('flex flex-col', className)}
    >
      <h2 className="pt-6 text-body font-medium text-text">{t('filtersTitle')}</h2>
      {facets.map((f) => (
        <FacetGroup key={f.key} facet={f} selected={draft[f.key] ?? []} onToggle={(v) => toggle(f.key, v)} />
      ))}
      {query.sort !== 'popular' ? <input type="hidden" name="sort" value={query.sort} /> : null}

      <div className="sticky bottom-0 z-10 -mx-5 mt-2 flex gap-2 bg-surface-raised px-5 py-4">
        <Button type="submit" size="s" className="flex-1">
          {t('apply')}
          {countSelected(draft) ? ` (${countSelected(draft)})` : ''}
        </Button>
        <Button
          href={resetHref}
          variant="menu"
          size="s"
          onClick={() => {
            setDraft({});
            onDone?.();
          }}
        >
          {t('reset')}
        </Button>
      </div>
    </form>
  );
}

function FacetGroup({ facet, selected, onToggle }: { facet: Facet; selected: string[]; onToggle: (value: string) => void }) {
  const t = useTranslations('catalog');
  const { fieldId } = useFieldIds();
  const [expanded, setExpanded] = useState(false);
  const [search, setSearch] = useState('');
  const title = t(`facets.${facet.key}`);

  const labelled = facet.values.map((v) => ({ ...v, text: facetValueLabel(t, facet.key, v) }));
  const matched = search ? labelled.filter((v) => v.text.toLowerCase().includes(search.trim().toLowerCase())) : labelled;
  // Выбранные значения видны всегда — иначе без JS они потерялись бы при отправке формы
  const visible = expanded || search ? matched : matched.filter((v, i) => i < VISIBLE || selected.includes(v.value));
  const hiddenCount = matched.length - visible.length;

  return (
    <details open className="group border-b border-border py-3" /* taste-skill-ignore: граница группы в форме фильтров */>
      <summary className="flex cursor-pointer list-none items-center justify-between gap-3 py-1.5 text-small font-medium text-text [&::-webkit-details-marker]:hidden">
        <span className="inline-flex items-center gap-2">
          {title}
          {selected.length ? (
            <span className="grid h-6 min-w-6 place-items-center rounded-pill bg-accent px-1.5 text-caption font-semibold text-text-on-accent">
              {selected.length}
            </span>
          ) : null}
        </span>
        <ChevronDown aria-hidden size={18} strokeWidth={1.5} className="shrink-0 text-text-secondary transition-transform group-open:rotate-180" />
      </summary>

      <fieldset className="mt-2">
        <legend className="sr-only">{title}</legend>
        {facet.values.length > SEARCH_FROM ? (
          <div className="relative mb-2">
            <label htmlFor={fieldId} className="sr-only">
              {t('searchValues')}: {title}
            </label>
            <Search aria-hidden size={16} strokeWidth={1.5} className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-text-secondary" />
            <input
              id={fieldId}
              type="search"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder={t('searchValues')}
              autoComplete="off"
              className="h-9 w-full rounded-sm border border-border bg-surface-strong pl-9 pr-3 text-small text-text outline-offset-0 placeholder:text-text-placeholder focus-visible:border-border-strong"
            />
          </div>
        ) : null}

        <ul className="flex flex-col">
          {visible.map((v) => {
            const checked = selected.includes(v.value);
            const disabled = v.count === 0 && !checked;
            return (
              <li key={v.value}>
                <label
                  className={cn(
                    'flex cursor-pointer items-center gap-3 rounded-sm py-1.5 text-small transition-colors',
                    disabled ? 'cursor-not-allowed opacity-40' : 'hover:text-accent',
                  )}
                >
                  <span className="relative inline-grid size-[18px] shrink-0 place-items-center">
                    <input
                      type="checkbox"
                      name={facet.key}
                      value={v.value}
                      checked={checked}
                      disabled={disabled}
                      onChange={() => onToggle(v.value)}
                      className="peer size-[18px] cursor-pointer appearance-none rounded-[5px] border border-text-secondary transition-colors checked:border-accent checked:bg-accent disabled:cursor-not-allowed"
                    />
                    <Check aria-hidden size={13} strokeWidth={3} className="pointer-events-none absolute text-base opacity-0 peer-checked:opacity-100" />
                  </span>
                  <span className={cn('min-w-0 flex-1', checked ? 'text-text' : 'text-text')}>{v.text}</span>
                  <span className="text-caption tabular-nums text-text-secondary">{v.count}</span>
                </label>
              </li>
            );
          })}
          {search && !matched.length ? <li className="py-1.5 text-small text-text-secondary">{t('noValues')}</li> : null}
        </ul>

        {!search && (hiddenCount > 0 || expanded) ? (
          <button
            type="button"
            onClick={() => setExpanded((e) => !e)}
            aria-expanded={expanded}
            className="mt-1 py-1 text-small font-medium text-accent transition-colors hover:text-accent-hover"
          >
            {expanded ? t('showLess') : t('showMore', { count: hiddenCount })}
          </button>
        ) : null}
      </fieldset>
    </details>
  );
}
