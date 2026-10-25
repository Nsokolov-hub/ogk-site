/**
 * Данные каталога из API сайта (поиск Meilisearch за /api/v1/public/catalog/*). Работают и на сервере,
 * и в браузере («Показать ещё»).
 */
import type { Locale } from '@/i18n/routing';
import type { CatalogFilters, CatalogListing, CatalogSort, FacetKey } from '@/types/catalog';
import { api, facetParams } from './backend';
import { orderFacets } from './catalog';

export async function getCatalogListing(p: {
  path: string[];
  filters: CatalogFilters;
  sort: CatalogSort;
  page: number;
  facetKeys: FacetKey[];
  pageSize?: number;
  locale: Locale;
  preset?: CatalogFilters;
}): Promise<CatalogListing> {
  const listing = await api<CatalogListing>(
    '/public/catalog/listing',
    {
      lang: p.locale,
      path: p.path.join('/'),
      sort: p.sort,
      page: p.page,
      pageSize: p.pageSize,
      facets: p.facetKeys.join(','),
      ...facetParams('f', p.filters),
      ...facetParams('p', p.preset),
    },
    { revalidate: 120, tags: ['catalog'] },
  );
  return { ...listing, facets: orderFacets(listing.facets) };
}

/** Число позиций в срезе — для правила индексации посадочных */
export async function countInScope(path: string[], preset?: CatalogFilters): Promise<number> {
  const { count } = await api<{ count: number }>('/public/catalog/count', { path: path.join('/'), ...facetParams('p', preset) }, { tags: ['catalog'] });
  return count;
}

/** Производители, представленные в разделе (блок «Производители» под сеткой) */
export async function getCategoryBrands(path: string[], preset?: CatalogFilters) {
  return api<{ slug: string; name: string; logo?: string | null; count: number }[]>(
    '/public/catalog/brands',
    { path: path.join('/'), ...facetParams('p', preset) },
    { tags: ['catalog'] },
  );
}
