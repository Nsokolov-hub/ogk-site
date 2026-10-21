'use client';

import { useEffect, useState } from 'react';
import { LayoutGrid, List, SearchX } from 'lucide-react';
import { useLocale, useTranslations } from 'next-intl';
import type { Locale } from '@/i18n/routing';
import type { CatalogListing } from '@/types/catalog';
import { ProductCard, ProductCardSkeleton } from '@/components/product/ProductCard';
import { Button } from '@/components/ui/Button';
import { catalogHref, countSelected, type CatalogQuery } from '@/lib/catalog';
import { getCatalogListing } from '@/lib/catalog-api';
import { useCatalogNav } from '@/lib/catalog-nav';
import { cn } from '@/lib/cn';
import { Pagination } from './Pagination';
import { ProductTable } from './ProductTable';

const VIEW_KEY = 'ogk-catalog-view';
type View = 'grid' | 'table';

/**
 * Выдача категории: первая страница приходит с сервера (SSR), «Показать ещё» догружает следующую.
 * Вид «Карточки / Таблица» запоминается в браузере.
 */
export function ProductListing({
  initial,
  path,
  basePath,
  query,
}: {
  initial: CatalogListing;
  path: string[];
  basePath: string;
  query: CatalogQuery;
}) {
  const t = useTranslations('catalog');
  const locale = useLocale() as Locale;
  const pending = useCatalogNav((s) => s.pending);
  const [items, setItems] = useState(initial.items);
  const [lastPage, setLastPage] = useState(initial.page);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(false);
  const [view, setView] = useState<View>('grid');

  useEffect(() => {
    try {
      if (window.localStorage.getItem(VIEW_KEY) === 'table') setView('table');
    } catch {
      // хранилище недоступно — остаёмся на карточках
    }
    // После смены фильтров или страницы возвращаем начало выдачи в поле зрения
    const el = document.getElementById('catalog-results');
    if (el && el.getBoundingClientRect().top < 0) el.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }, []);

  const changeView = (v: View) => {
    setView(v);
    try {
      window.localStorage.setItem(VIEW_KEY, v);
    } catch {
      // не критично
    }
  };

  const loadMore = async () => {
    if (loading) return;
    setLoading(true);
    setError(false);
    try {
      const res = await getCatalogListing({ path, filters: query.filters, sort: query.sort, page: lastPage + 1, facetKeys: [], locale });
      setItems((prev) => [...prev, ...res.items]);
      setLastPage(res.page);
    } catch {
      setError(true);
    } finally {
      setLoading(false);
    }
  };

  const viewBtn = (v: View, label: string, Icon: typeof LayoutGrid) => (
    <button
      type="button"
      aria-pressed={view === v}
      onClick={() => changeView(v)}
      className={cn(
        'inline-flex h-9 items-center gap-2 rounded-pill px-3 text-small font-medium transition-colors',
        view === v ? 'bg-accent text-text-on-accent' : 'text-text-secondary hover:text-text',
      )}
    >
      <Icon aria-hidden size={16} strokeWidth={1.5} />
      <span className="hidden sm:inline">{label}</span>
      <span className="sr-only sm:hidden">{label}</span>
    </button>
  );

  return (
    <div id="catalog-results" className="scroll-mt-28">
      <div className="mt-4 flex flex-wrap items-center justify-between gap-3">
        <p className="text-small text-text-secondary" aria-live="polite">
          {t('found', { count: initial.total })}
        </p>
        <div role="group" aria-label={t('view')} className="inline-flex rounded-pill bg-surface p-0.5">
          {viewBtn('grid', t('viewGrid'), LayoutGrid)}
          {viewBtn('table', t('viewTable'), List)}
        </div>
      </div>

      <div aria-busy={pending || loading} className={cn('mt-4 transition-opacity duration-200', pending && 'pointer-events-none opacity-50')}>
        {items.length === 0 ? (
          <div className="flex flex-col items-start gap-4 rounded-block bg-surface p-6 md:p-10">
            <SearchX aria-hidden size={32} strokeWidth={1.5} className="text-accent" />
            <h2 className="text-h4 font-medium text-text">{t('empty.title')}</h2>
            <p className="max-w-[560px] text-body text-text-secondary">{t('empty.text')}</p>
            <div className="flex flex-wrap gap-3">
              {countSelected(query.filters) ? (
                <Button href={catalogHref(basePath, { sort: query.sort })} variant="menu" size="m">
                  {t('empty.reset')}
                </Button>
              ) : null}
              <Button href="#catalog-request" size="m">
                {t('empty.request')}
              </Button>
            </div>
          </div>
        ) : view === 'grid' ? (
          <ul className="grid grid-cols-1 gap-3 sm:grid-cols-2 md:grid-cols-3 md:gap-5 lg:grid-cols-2 xl:grid-cols-3 2xl:gap-6">
            {items.map((p, i) => (
              <li key={p.id}>
                <ProductCard product={p} size="md" place="list" priority={i < 3 && lastPage === initial.page} />
              </li>
            ))}
            {loading
              ? Array.from({ length: 3 }, (_, i) => (
                  <li key={`sk-${i}`}>
                    <ProductCardSkeleton />
                  </li>
                ))
              : null}
          </ul>
        ) : (
          <ProductTable items={items} caption={t('tableCaption')} />
        )}
      </div>

      {error ? (
        <p role="alert" className="mt-6 text-center text-small text-error">
          {t('loadError')}
        </p>
      ) : null}

      {lastPage < initial.pageCount ? (
        <div className="mt-8 flex justify-center">
          <Button variant="menu" size="m" aria-disabled={loading || undefined} onClick={() => void loadMore()}>
            {loading ? t('loading') : t('showMorePage')}
          </Button>
        </div>
      ) : null}

      <Pagination basePath={basePath} query={query} start={initial.page} end={lastPage} pageCount={initial.pageCount} />
    </div>
  );
}
