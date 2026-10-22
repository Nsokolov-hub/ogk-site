import type { CardType } from '@/types/catalog';

/** Общие типы и константы подсказок поиска — без данных, чтобы не тянуть каталог в браузер */

export interface SuggestItem {
  id: string;
  slug: string;
  name: string;
  brand: string;
  catalogNumber: string;
  cas?: string;
  /** Брутто-формула — когда совпадение по формуле */
  formula?: string;
  cardType: CardType;
  /** По какому полю совпало — подсвечиваем в выдаче */
  match: 'catalogNumber' | 'cas' | 'formula' | 'name' | 'brand';
}

export interface SuggestResult {
  query: string;
  /** Запрос в исправленной раскладке, если по исходному ничего не нашлось */
  corrected?: string;
  items: SuggestItem[];
  /** Всего товаров по запросу */
  total: number;
  /** Группы подсказок (SRCH-01): субстанции, категории, бренды */
  substances: { slug: string; name: string; nameEn: string }[];
  categories: { name: string; href: string }[];
  brands: { slug: string; name: string }[];
}

export const SUGGEST_MIN = 2;
export const SUGGEST_LIMIT = 6;
