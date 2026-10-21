import type { CatalogFilters, CatalogSort, Facet, FacetKey, ProductPreview } from '@/types/catalog';

/**
 * Каталог: параметры URL, фильтрация, сортировка и фасеты.
 * Сейчас считается по мокам; в проде это делает поиск (Meilisearch) на бэкенде.
 * Формат URL (ТЗ URL-06): ?brand=edqm&brand=usp&pack=100-mg&sort=name&page=2
 */

export const PAGE_SIZE = 24;

export const FACET_KEYS: FacetKey[] = ['brand', 'availability', 'pack', 'storage', 'purpose', 'type', 'phase', 'length', 'diameter', 'particle', 'ph'];
const SORTS: CatalogSort[] = ['popular', 'name', 'availability'];

/** Значения, которые переводятся через messages (catalog.values.*); остальные выводятся как есть */
export const TRANSLATED_FACETS: FacetKey[] = ['availability', 'storage', 'purpose', 'type'];

export type SearchParams = Record<string, string | string[] | undefined>;

export interface CatalogQuery {
  filters: CatalogFilters;
  sort: CatalogSort;
  page: number;
}

const VALUE_RE = /^[a-z0-9.\-]{1,40}$/i;

export function parseCatalogQuery(sp: SearchParams): CatalogQuery {
  const filters: CatalogFilters = {};
  for (const key of FACET_KEYS) {
    const raw = sp[key];
    const list = (Array.isArray(raw) ? raw : raw ? [raw] : []).flatMap((v) => v.split(',')).filter((v) => VALUE_RE.test(v));
    if (list.length) filters[key] = Array.from(new Set(list));
  }
  const sortRaw = typeof sp.sort === 'string' ? sp.sort : undefined;
  const sort = SORTS.includes(sortRaw as CatalogSort) ? (sortRaw as CatalogSort) : 'popular';
  const pageNum = Number.parseInt(typeof sp.page === 'string' ? sp.page : '1', 10);
  return { filters, sort, page: Number.isFinite(pageNum) && pageNum > 0 ? pageNum : 1 };
}

export function countSelected(filters: CatalogFilters) {
  return Object.values(filters).reduce((n, v) => n + (v?.length ?? 0), 0);
}

/** Ссылка на страницу каталога с фильтрами; порядок параметров стабильный */
export function catalogHref(basePath: string, q: Partial<CatalogQuery>): string {
  const params = new URLSearchParams();
  for (const key of FACET_KEYS) {
    for (const v of q.filters?.[key] ?? []) params.append(key, v);
  }
  if (q.sort && q.sort !== 'popular') params.set('sort', q.sort);
  if (q.page && q.page > 1) params.set('page', String(q.page));
  const s = params.toString();
  return s ? `${basePath}?${s}` : basePath;
}

/** Фильтры без одного значения — для чипов «×» */
export function withoutValue(filters: CatalogFilters, key: FacetKey, value: string): CatalogFilters {
  const next: CatalogFilters = { ...filters, [key]: (filters[key] ?? []).filter((v) => v !== value) };
  if (!next[key]?.length) delete next[key];
  return next;
}

/** Внутри одного фильтра — «или», между фильтрами — «и» */
export function applyFilters(items: ProductPreview[], filters: CatalogFilters, except?: FacetKey) {
  const active = (Object.entries(filters) as [FacetKey, string[]][]).filter(([k, v]) => k !== except && v.length);
  if (!active.length) return items;
  return items.filter((p) => active.every(([k, values]) => (p.attributes?.[k] ?? []).some((v) => values.includes(v))));
}

export function sortItems(items: ProductPreview[], sort: CatalogSort) {
  const inStock = (p: ProductPreview) => (p.availability === 'in_stock' ? 0 : 1);
  const byName = (a: ProductPreview, b: ProductPreview) => a.name.localeCompare(b.name, 'en');
  const list = [...items];
  if (sort === 'name') return list.sort(byName);
  if (sort === 'availability') return list.sort((a, b) => inStock(a) - inStock(b) || byName(a, b));
  return list.sort((a, b) => inStock(a) - inStock(b) || (b.popularity ?? 0) - (a.popularity ?? 0) || byName(a, b));
}

// ── порядок значений в фасетах ──
const UNIT_ORDER = ['mg', 'g', 'ml', 'l', 'pcs', 'vial', 'pack'];
const FIXED_ORDER: Partial<Record<FacetKey, string[]>> = {
  availability: ['in_stock', 'on_request'],
  storage: ['room', '2-8', '-20', '-80'],
  purpose: ['assay', 'identification', 'impurity-control', 'system-suitability'],
  type: ['api', 'impurity', 'metabolite', 'labeled'],
};

function packWeight(key: string) {
  if (key === 'custom') return Number.MAX_SAFE_INTEGER;
  const m = key.match(/^([\d-]+?)-([a-z]+)$/);
  if (!m) return Number.MAX_SAFE_INTEGER - 1;
  const n = Number.parseFloat(m[1].replace('-', '.'));
  const u = UNIT_ORDER.indexOf(m[2]);
  return (u < 0 ? 99 : u) * 1e6 + n;
}

function compareValues(key: FacetKey, a: { value: string; count: number; label: string }, b: { value: string; count: number; label: string }) {
  const fixed = FIXED_ORDER[key];
  if (fixed) return fixed.indexOf(a.value) - fixed.indexOf(b.value);
  if (key === 'pack') return packWeight(a.value) - packWeight(b.value);
  if (key === 'length' || key === 'diameter' || key === 'particle') return Number(a.value) - Number(b.value);
  if (key === 'brand') return b.count - a.count || a.label.localeCompare(b.label);
  return a.label.localeCompare(b.label);
}

/** Подписи значений, которые берутся из данных (бренд, фасовка) */
function valueLabel(key: FacetKey, value: string, items: ProductPreview[]): string {
  if (key === 'brand') return items.find((p) => p.brand.slug === value)?.brand.name ?? value;
  if (key === 'pack') {
    for (const p of items) {
      const pk = p.packagings.find((x) => x.id.endsWith(`-${value}`));
      if (pk) return pk.label;
    }
    return value;
  }
  if (key === 'ph') return value.replace('-', '–').replace(/\./g, ',');
  if (key === 'particle' || key === 'diameter') return value.replace('.', ',');
  return value;
}

/**
 * Фасеты со счётчиками: для каждого фильтра считаем позиции с учётом всех остальных выбранных фильтров.
 * Так у выбранного фильтра видны альтернативы, а не только он сам.
 */
export function buildFacets(items: ProductPreview[], filters: CatalogFilters, keys: FacetKey[]): Facet[] {
  return keys
    .map((key) => {
      const scoped = applyFilters(items, filters, key);
      const counts = new Map<string, number>();
      for (const p of scoped) for (const v of p.attributes?.[key] ?? []) counts.set(v, (counts.get(v) ?? 0) + 1);
      const selected = filters[key] ?? [];
      for (const v of selected) if (!counts.has(v)) counts.set(v, 0);
      const values = Array.from(counts, ([value, count]) => ({
        value,
        count,
        label: key === 'pack' && value === 'custom' ? 'custom' : valueLabel(key, value, items),
        selected: selected.includes(value),
      })).sort((a, b) => compareValues(key, a, b));
      return { key, values };
    })
    .filter((f) => f.values.length > 1 || f.values.some((v) => v.selected));
}
