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
  /** Страницы веществ по CAS (/cas/<cas>/) для CAS или его начала — все варианты вещества */
  casPages?: CasPageLink[];
  /** Целый CAS с неверной контрольной цифрой и ничего не найдено — просим проверить номер */
  casTypo?: boolean;
}

export interface CasPageLink {
  cas: string;
  name: string;
  offers: number;
  /** Наше русское название вещества, если оно есть: по нему страницу находят и в русском поиске */
  nameRu?: string | null;
}

export const SUGGEST_MIN = 2;
export const SUGGEST_LIMIT = 6;
