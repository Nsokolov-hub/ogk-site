import type { ProductPreview } from '@/types/catalog';
import { catalogProducts } from '@/data/mock/catalog-products';
import { SUGGEST_LIMIT, SUGGEST_MIN, type SuggestItem, type SuggestResult } from './search-shared';

export type { SuggestItem, SuggestResult } from './search-shared';

/**
 * Подсказки поиска (ТЗ 6, SRCH-01). Сейчас считаются по мокам на сервере;
 * в проде это Meilisearch за /api/v1/public/search/suggest — меняется только тело suggest().
 *
 * Порядок: точный кат. № или CAS → начало кат. № / CAS → название с начала слова → вхождение в название.
 */

/** Кат. № и CAS сравниваем без пробелов, дефисов и точек: «1.00030» = «100030», «58 08 2» = «58-08-2» */
const compact = (s: string) => s.toLowerCase().replace(/[\s.\-–/]/g, '');
const words = (s: string) => s.toLowerCase().split(/[\s,;()[\]]+/).filter(Boolean);

function rank(p: ProductPreview, q: string, qc: string): [number, SuggestItem['match']] | null {
  const num = compact(p.catalogNumber);
  const cas = p.cas ? compact(p.cas) : '';
  if (qc && (num === qc || cas === qc)) return [0, num === qc ? 'catalogNumber' : 'cas'];
  if (qc.length >= 3 && num.startsWith(qc)) return [1, 'catalogNumber'];
  if (qc.length >= 3 && cas && cas.startsWith(qc)) return [1, 'cas'];
  const name = p.name.toLowerCase();
  if (words(name).some((w) => w.startsWith(q))) return [name.startsWith(q) ? 2 : 3, 'name'];
  if (name.includes(q)) return [4, 'name'];
  return null;
}

export function suggest(query: string, limit = SUGGEST_LIMIT): SuggestResult {
  const q = query.trim().toLowerCase().replace(/\s+/g, ' ');
  if (q.length < SUGGEST_MIN) return { query, items: [], total: 0 };
  const qc = compact(q);

  const found: { p: ProductPreview; r: number; match: SuggestItem['match'] }[] = [];
  for (const p of catalogProducts) {
    const res = rank(p, q, qc);
    if (res) found.push({ p, r: res[0], match: res[1] });
  }
  found.sort((a, b) => a.r - b.r || (b.p.popularity ?? 0) - (a.p.popularity ?? 0) || a.p.name.localeCompare(b.p.name, 'en'));

  return {
    query,
    total: found.length,
    items: found.slice(0, limit).map(({ p, match }) => ({
      id: p.id,
      slug: p.slug,
      name: p.name,
      brand: p.brand.name,
      catalogNumber: p.catalogNumber,
      cas: p.cas,
      cardType: p.cardType,
      match,
    })),
  };
}

// ── страница результатов /search/ (SRCH-07) ──

export interface SearchFacetValue {
  value: string;
  label: string;
  count: number;
  selected: boolean;
}

export interface SearchPageResult {
  query: string;
  items: ProductPreview[];
  total: number;
  page: number;
  pageCount: number;
  facets: { brand: SearchFacetValue[]; category: SearchFacetValue[] };
}

export const SEARCH_PAGE_SIZE = 24;

/** Полная выдача с фильтрами по бренду и разделу и счётчиками; порядок — как у подсказок (SRCH-04) */
export function searchCatalog(p: {
  query: string;
  brand?: string;
  category?: string;
  page?: number;
  categoryNames: Record<string, string>;
}): SearchPageResult {
  const q = p.query.trim().toLowerCase().replace(/\s+/g, ' ');
  const empty = { query: p.query, items: [], total: 0, page: 1, pageCount: 1, facets: { brand: [], category: [] } };
  if (q.length < SUGGEST_MIN) return empty;
  const qc = compact(q);

  const found: { p: ProductPreview; r: number }[] = [];
  for (const prod of catalogProducts) {
    const res = rank(prod, q, qc);
    if (res) found.push({ p: prod, r: res[0] });
  }
  found.sort((a, b) => a.r - b.r || (b.p.popularity ?? 0) - (a.p.popularity ?? 0) || a.p.name.localeCompare(b.p.name, 'en'));
  const all = found.map((f) => f.p);
  const topOf = (prod: ProductPreview) => prod.categorySlug.split('/')[0];

  // Счётчики фасета считаем с учётом другого фильтра — так видны альтернативы
  const byBrand = all.filter((x) => !p.category || topOf(x) === p.category);
  const byCategory = all.filter((x) => !p.brand || x.brand.slug === p.brand);
  const count = (list: ProductPreview[], key: (x: ProductPreview) => string, label: (x: ProductPreview) => string, selected?: string) => {
    const m = new Map<string, SearchFacetValue>();
    for (const x of list) {
      const k = key(x);
      const v = m.get(k) ?? { value: k, label: label(x), count: 0, selected: k === selected };
      v.count += 1;
      m.set(k, v);
    }
    if (selected && !m.has(selected)) m.set(selected, { value: selected, label: selected, count: 0, selected: true });
    return Array.from(m.values()).sort((a, b) => b.count - a.count || a.label.localeCompare(b.label));
  };

  const filtered = all.filter((x) => (!p.brand || x.brand.slug === p.brand) && (!p.category || topOf(x) === p.category));
  const pageCount = Math.max(1, Math.ceil(filtered.length / SEARCH_PAGE_SIZE));
  const page = Math.min(Math.max(1, p.page ?? 1), pageCount);

  return {
    query: p.query,
    items: filtered.slice((page - 1) * SEARCH_PAGE_SIZE, page * SEARCH_PAGE_SIZE),
    total: filtered.length,
    page,
    pageCount,
    facets: {
      brand: count(byBrand, (x) => x.brand.slug, (x) => x.brand.name, p.brand),
      category: count(byCategory, topOf, (x) => p.categoryNames[topOf(x)] ?? topOf(x), p.category),
    },
  };
}

// ── пакетный поиск по списку (SRCH-09, SC-02) ──

export const BATCH_LIMIT = 200;

export type BatchCandidate = Pick<
  ProductPreview,
  'id' | 'slug' | 'name' | 'brand' | 'catalogNumber' | 'cas' | 'categorySlug' | 'packagings' | 'customPackaging' | 'cardType'
>;

export interface BatchLineResult {
  line: string;
  query: string;
  quantity: number;
  /** exact — найдено точно; multiple — несколько кандидатов, нужен выбор; none — свободная строка */
  status: 'exact' | 'multiple' | 'none';
  candidates: BatchCandidate[];
}

const toCandidate = (x: ProductPreview): BatchCandidate => ({
  id: x.id,
  slug: x.slug,
  name: x.name,
  brand: x.brand,
  catalogNumber: x.catalogNumber,
  cas: x.cas,
  categorySlug: x.categorySlug,
  packagings: x.packagings,
  customPackaging: x.customPackaging,
  cardType: x.cardType,
});

/** «Y0001897 2», «28721-07-5;3», «Paracetamol CRS» → запрос и количество */
export function parseLine(line: string): { query: string; quantity: number } {
  const cols = line.split(/\t|;/).map((c) => c.trim()).filter(Boolean);
  if (cols.length >= 2 && /^\d{1,3}$/.test(cols[cols.length - 1])) {
    return { query: cols.slice(0, -1).join(' '), quantity: Number(cols[cols.length - 1]) };
  }
  const words = line.trim().split(/\s+/);
  if (words.length === 2 && /^\d{1,3}$/.test(words[1]) && /\d/.test(words[0])) {
    return { query: words[0], quantity: Number(words[1]) };
  }
  return { query: line.trim(), quantity: 1 };
}

export function matchLines(lines: string[]): BatchLineResult[] {
  return lines
    .map((l) => l.trim())
    .filter(Boolean)
    .slice(0, BATCH_LIMIT)
    .map((line) => {
      const { query, quantity } = parseLine(line);
      const q = query.toLowerCase();
      const qc = compact(q);
      // Точный кат. № или CAS — без исправления опечаток (SRCH-03)
      const exact = catalogProducts.filter((x) => compact(x.catalogNumber) === qc || (x.cas && compact(x.cas) === qc));
      let candidates = exact;
      if (!candidates.length && q.length >= 3) {
        candidates = catalogProducts
          .map((x) => ({ x, r: rank(x, q, qc) }))
          .filter((m) => m.r && m.r[0] <= 3)
          .sort((a, b) => a.r![0] - b.r![0] || (b.x.popularity ?? 0) - (a.x.popularity ?? 0))
          .slice(0, 5)
          .map((m) => m.x);
      }
      const status: BatchLineResult['status'] = candidates.length === 0 ? 'none' : candidates.length === 1 ? 'exact' : 'multiple';
      return { line, query, quantity: Math.max(1, Math.min(999, quantity)), status, candidates: candidates.slice(0, 5).map(toCandidate) };
    });
}
