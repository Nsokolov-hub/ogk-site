'use client';

import { useRef, useState } from 'react';
import { useTranslations } from 'next-intl';
import type { Locale } from '@/i18n/routing';
import type { ProductPreview } from '@/types/catalog';
import { ProductCard, ProductCardSkeleton } from '@/components/product/ProductCard';
import { Button } from '@/components/ui/Button';
import { getHomeProducts, type HomeProductsSort } from '@/lib/api';
import { cn } from '@/lib/cn';

const PAGE = 12;
const SORTS: HomeProductsSort[] = ['popular', 'alpha'];

/** Переключатель «Популярные / По алфавиту» (URL не меняется), сетка и «Загрузить ещё» по 12 */
export function ProductsGrid({ initial, initialTotal, locale }: { initial: ProductPreview[]; initialTotal: number; locale: Locale }) {
  const t = useTranslations('home.products');
  const [sort, setSort] = useState<HomeProductsSort>('popular');
  const [items, setItems] = useState(initial);
  const [total, setTotal] = useState(initialTotal);
  const [loading, setLoading] = useState<'sort' | 'more' | null>(null);
  const [error, setError] = useState(false);
  const requestId = useRef(0);

  const load = async (nextSort: HomeProductsSort, offset: number, mode: 'sort' | 'more') => {
    const id = ++requestId.current;
    setLoading(mode);
    setError(false);
    try {
      const res = await getHomeProducts({ sort: nextSort, offset, limit: PAGE, locale });
      if (id !== requestId.current) return;
      setItems((prev) => (mode === 'more' ? [...prev, ...res.items] : res.items));
      setTotal(res.total);
    } catch {
      if (id === requestId.current) setError(true);
    } finally {
      if (id === requestId.current) setLoading(null);
    }
  };

  const changeSort = (next: HomeProductsSort) => {
    if (next === sort) return;
    setSort(next);
    void load(next, 0, 'sort');
  };

  return (
    <>
      <div className="mt-8 flex flex-wrap items-center justify-between gap-4 lg:mt-10">
        <div role="group" aria-label={t('sortLabel')} className="inline-flex rounded-pill bg-surface p-1">
          {SORTS.map((s) => (
            <button
              key={s}
              type="button"
              aria-pressed={sort === s}
              onClick={() => changeSort(s)}
              className={cn(
                'h-10 rounded-pill px-5 text-small font-medium transition-colors md:text-body',
                sort === s ? 'bg-accent text-text-on-accent' : 'text-text-secondary hover:text-text',
              )}
            >
              {t(s)}
            </button>
          ))}
        </div>
        <p className="text-small text-text-secondary" aria-live="polite">
          {loading === 'sort' ? t('loading') : t('shown', { shown: items.length, total })}
        </p>
      </div>

      <ul aria-busy={loading !== null} className="mt-6 grid grid-cols-1 gap-3 sm:grid-cols-2 md:gap-6 lg:grid-cols-3 xl:grid-cols-4 2xl:gap-[34px]">
        {loading === 'sort'
          ? Array.from({ length: PAGE }, (_, i) => (
              <li key={`s${i}`}>
                <ProductCardSkeleton />
              </li>
            ))
          : items.map((p) => (
              <li key={p.id}>
                <ProductCard product={p} size="sm" place="list" />
              </li>
            ))}
        {loading === 'more'
          ? Array.from({ length: 4 }, (_, i) => (
              <li key={`m${i}`}>
                <ProductCardSkeleton />
              </li>
            ))
          : null}
      </ul>

      {error ? (
        <p role="alert" className="mt-6 text-center text-small text-error">
          {t('error')}
        </p>
      ) : null}

      {items.length < total ? (
        <div className="mt-10 flex justify-center">
          <Button
            variant="menu"
            size="m"
            aria-disabled={loading !== null || undefined}
            onClick={() => {
              if (loading === null) void load(sort, items.length, 'more');
            }}
          >
            {loading === 'more' ? t('loading') : t('loadMore')}
          </Button>
        </div>
      ) : null}
    </>
  );
}
