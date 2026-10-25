/**
 * Поиск по каталогу (ТЗ 6) — Meilisearch за API сайта /api/v1/public/search/*.
 * Порядок выдачи считает бэкенд (SRCH-04): точный кат. № или CAS → брутто-формула → полнотекст; при равенстве
 * выше товары в наличии и с высокой полнотой. Пустая выдача повторяется в другой раскладке (SRCH-05).
 */
import type { ProductPreview } from '@/types/catalog';
import { api } from './backend';
import type { SuggestResult } from './search-shared';

export type { SuggestItem, SuggestResult } from './search-shared';

export async function suggest(query: string, lang: string): Promise<SuggestResult> {
  return api<SuggestResult>('/public/search/suggest', { q: query.slice(0, 100), lang }, { revalidate: 60, tags: ['catalog'] });
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
  /** Запрос в исправленной раскладке, если по исходному ничего не нашлось */
  corrected?: string | null;
  items: ProductPreview[];
  total: number;
  page: number;
  pageCount: number;
  facets: { brand: SearchFacetValue[]; category: SearchFacetValue[] };
}

export const SEARCH_PAGE_SIZE = 24;

/** Полная выдача с фильтрами по бренду и разделу и счётчиками. Пустой результат API пишет в «спрос без товара» */
export async function searchCatalog(p: { query: string; brand?: string; category?: string; page?: number; locale: string }): Promise<SearchPageResult> {
  return api<SearchPageResult>(
    '/public/search',
    { q: p.query, brand: p.brand, category: p.category, page: p.page, lang: p.locale },
    { revalidate: false },
  );
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
