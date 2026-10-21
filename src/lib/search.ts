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
