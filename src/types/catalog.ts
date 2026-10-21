/** Три типа карточек (ТЗ 5.2): стандарты и реактивы / оборудование и колонки / прочее */
export type CardType = 'standard' | 'equipment' | 'other';

export type PackUnit = 'mg' | 'g' | 'ml' | 'pcs';

export interface Packaging {
  id: string;
  /** «100 мг», «1 л», «1 шт.» */
  label: string;
  /** Свой кат. № фасовки, если есть */
  catalogNumber?: string;
}

export interface BrandRef {
  slug: string;
  name: string;
  logo?: string;
}

export interface ProductPreview {
  id: string;
  /** URL: /product/{slug}/ */
  slug: string;
  cardType: CardType;
  /** Название EN от производителя, может быть очень длинным */
  name: string;
  brand: BrandRef;
  /** Кат. № или P/N */
  catalogNumber: string;
  cas?: string;
  /** Основная категория */
  categorySlug: string;
  packagings: Packaging[];
  /** «Любая фасовка под запрос» (5.2.2) */
  customPackaging: boolean;
  image?: { src: string; alt: string; kind: 'photo' | 'structure' };
  discontinued?: boolean;
  /** Значения для фильтров каталога (атрибуты типа, ТЗ 5.1): ключ фильтра → значения */
  attributes?: Partial<Record<FacetKey, string[]>>;
  /** Популярность для сортировки по умолчанию */
  popularity?: number;
}

/** Фильтры каталога (ТЗ 5.5). Набор задаётся в категории. */
export type FacetKey =
  | 'brand'
  | 'pack'
  | 'storage'
  | 'purpose'
  | 'type'
  | 'phase'
  | 'length'
  | 'diameter'
  | 'particle'
  | 'ph';

export type CatalogFilters = Partial<Record<FacetKey, string[]>>;

/** По популярности / по названию A–Z. Все товары под заказ, поэтому сортировки по наличию нет. */
export type CatalogSort = 'popular' | 'name';

export interface FacetValue {
  value: string;
  label: string;
  count: number;
  selected: boolean;
}

export interface Facet {
  key: FacetKey;
  values: FacetValue[];
}

export interface CatalogListing {
  items: ProductPreview[];
  total: number;
  page: number;
  pageSize: number;
  pageCount: number;
  facets: Facet[];
}

export interface Category {
  slug: string;
  name: string;
  /** /catalog/reference-standards/edqm/ */
  href: string;
  children?: Category[];
}
