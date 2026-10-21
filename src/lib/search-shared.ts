import type { CardType } from '@/types/catalog';

/** Общие типы и константы подсказок поиска — без данных, чтобы не тянуть каталог в браузер */

export interface SuggestItem {
  id: string;
  slug: string;
  name: string;
  brand: string;
  catalogNumber: string;
  cas?: string;
  cardType: CardType;
  /** По какому полю совпало — подсвечиваем в выдаче */
  match: 'catalogNumber' | 'cas' | 'name';
}

export interface SuggestResult {
  query: string;
  items: SuggestItem[];
  total: number;
}

export const SUGGEST_MIN = 2;
export const SUGGEST_LIMIT = 6;
