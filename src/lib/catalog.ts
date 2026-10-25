import type { CatalogFilters, CatalogSort, Facet, FacetKey } from '@/types/catalog';

/**
 * Каталог: параметры URL и порядок значений в фильтрах. Фильтрует, сортирует и считает фасеты поиск на бэкенде.
 * Формат URL (ТЗ URL-06): ?brand=edqm&brand=usp&pack=100-mg&sort=name&page=2
 */

export const PAGE_SIZE = 24;

export const FACET_KEYS: FacetKey[] = ['brand', 'pack', 'storage', 'purpose', 'type', 'phase', 'length', 'diameter', 'particle', 'ph'];
const SORTS: CatalogSort[] = ['popular', 'name'];

/** Значения, которые переводятся через messages (catalog.values.*); остальные выводятся как есть */
export const TRANSLATED_FACETS: FacetKey[] = ['storage', 'purpose', 'type'];

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

// ── порядок значений в фасетах ──
const UNIT_ORDER = ['ug', 'mg', 'g', 'kg', 'ul', 'ml', 'l', 'pcs', 'test', 'kit', 'vial', 'pack'];
const FIXED_ORDER: Partial<Record<FacetKey, string[]>> = {
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

/** Подписи чисел в фильтрах колонок: pH 2–8, 2,7 мкм */
function valueLabel(key: FacetKey, value: string, label: string): string {
  if (key === 'ph') return value.replace('-', '–').replace(/\./g, ',');
  if (key === 'particle' || key === 'diameter') return value.replace('.', ',');
  return label;
}

/**
 * Значения фасетов в понятном порядке (фасовки по весу, хранение по температуре). Счётчики уже посчитаны API:
 * у выбранного фильтра — с учётом всех остальных фильтров, так видны альтернативы. Фильтр из одного значения
 * без выбора не показываем.
 */
export function orderFacets(facets: Facet[]): Facet[] {
  return facets
    .map((f) => ({
      key: f.key,
      values: f.values
        .map((v) => ({ ...v, label: f.key === 'pack' && v.value === 'custom' ? 'custom' : valueLabel(f.key, v.value, v.label) }))
        // В длинных списках (фасовки большого раздела) первыми идут ходовые значения, в коротких — по порядку
        .sort((a, b) => (f.values.length > 15 && f.key === 'pack' ? b.count - a.count || compareValues(f.key, a, b) : compareValues(f.key, a, b))),
    }))
    .filter((f) => f.values.length > 1 || f.values.some((v) => v.selected));
}
