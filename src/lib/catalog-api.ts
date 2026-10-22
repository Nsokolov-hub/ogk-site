/**
 * Данные каталога. Работают и на сервере, и в браузере («Показать ещё»).
 * Сейчас — моки; позже тело заменится на fetch к /api/v1/public/catalog — сигнатура остаётся.
 */
import type { Locale } from '@/i18n/routing';
import type { CatalogFilters, CatalogListing, CatalogSort, FacetKey } from '@/types/catalog';
import { catalogProducts } from '@/data/mock/catalog-products';
import { applyFilters, buildFacets, PAGE_SIZE, sortItems } from './catalog';
import { localizeProduct } from './pack-label';

async function networkDelay(ms = 350) {
  if (typeof window !== 'undefined') await new Promise((r) => setTimeout(r, ms));
}

/**
 * Позиции категории: путь [] — весь каталог, ['reference-standards'] — раздел, ['reference-standards','edqm'] — подраздел.
 * preset — фиксированные фильтры SEO-посадочной (URL-07): срез внутри категории.
 */
function scope(path: string[], preset?: CatalogFilters) {
  const key = path.join('/');
  const items = path.length ? catalogProducts.filter((p) => p.categorySlug === key || p.categorySlug.startsWith(`${key}/`)) : catalogProducts;
  return preset ? applyFilters(items, preset) : items;
}

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
  await networkDelay();
  const pageSize = p.pageSize ?? PAGE_SIZE;
  // Подписи фасовок — на языке страницы (и в карточках, и в фильтре «Фасовка»)
  const base = scope(p.path, p.preset).map((x) => localizeProduct(x, p.locale));
  const filtered = sortItems(applyFilters(base, p.filters), p.sort);
  const pageCount = Math.max(1, Math.ceil(filtered.length / pageSize));
  const page = Math.min(Math.max(1, p.page), pageCount);
  return {
    items: filtered.slice((page - 1) * pageSize, page * pageSize),
    total: filtered.length,
    page,
    pageSize,
    pageCount,
    facets: buildFacets(base, p.filters, p.facetKeys),
  };
}

/** Число позиций в срезе — для правила индексации посадочных */
export function countInScope(path: string[], preset?: CatalogFilters) {
  return scope(path, preset).length;
}

/** Производители, представленные в разделе (блок «Производители» под сеткой) */
export async function getCategoryBrands(path: string[], preset?: CatalogFilters) {
  const map = new Map<string, { slug: string; name: string; logo?: string; count: number }>();
  for (const p of scope(path, preset)) {
    const b = map.get(p.brand.slug) ?? { ...p.brand, count: 0 };
    b.count += 1;
    map.set(p.brand.slug, b);
  }
  return Array.from(map.values()).sort((a, b) => b.count - a.count);
}
