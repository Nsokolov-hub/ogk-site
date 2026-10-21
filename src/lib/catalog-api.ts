/**
 * Данные каталога. Работают и на сервере, и в браузере («Показать ещё»).
 * Сейчас — моки; позже тело заменится на fetch к /api/v1/public/catalog — сигнатура остаётся.
 */
import type { Locale } from '@/i18n/routing';
import type { CatalogFilters, CatalogListing, CatalogSort, FacetKey } from '@/types/catalog';
import { catalogProducts } from '@/data/mock/catalog-products';
import { applyFilters, buildFacets, PAGE_SIZE, sortItems } from './catalog';

async function networkDelay(ms = 350) {
  if (typeof window !== 'undefined') await new Promise((r) => setTimeout(r, ms));
}

/** Позиции категории: путь [] — весь каталог, ['reference-standards'] — раздел, ['reference-standards','edqm'] — подраздел */
function scope(path: string[]) {
  if (!path.length) return catalogProducts;
  const key = path.join('/');
  return catalogProducts.filter((p) => p.categorySlug === key || p.categorySlug.startsWith(`${key}/`));
}

export async function getCatalogListing(p: {
  path: string[];
  filters: CatalogFilters;
  sort: CatalogSort;
  page: number;
  facetKeys: FacetKey[];
  pageSize?: number;
  locale: Locale;
}): Promise<CatalogListing> {
  await networkDelay();
  const pageSize = p.pageSize ?? PAGE_SIZE;
  const base = scope(p.path);
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

/** Производители, представленные в разделе (блок «Производители» под сеткой) */
export async function getCategoryBrands(path: string[]) {
  const map = new Map<string, { slug: string; name: string; logo?: string; count: number }>();
  for (const p of scope(path)) {
    const b = map.get(p.brand.slug) ?? { ...p.brand, count: 0 };
    b.count += 1;
    map.set(p.brand.slug, b);
  }
  return Array.from(map.values()).sort((a, b) => b.count - a.count);
}
