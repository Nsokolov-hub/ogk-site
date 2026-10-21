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
  /** Связь с субстанцией (ТЗ 5.1): страница /substances/{slug}/ и блок «Другие примеси» */
  substance?: { slug: string; role: SubstanceRole };
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

/** Роль позиции относительно субстанции (ТЗ 5.1): стандарт API, примесь, метаболит, меченое соединение */
export type SubstanceRole = 'api' | 'impurity' | 'metabolite' | 'labeled';

export type StorageCondition = 'room' | '2-8' | '-20' | '-80';
export type ShippingCondition = 'ambient' | 'cold-chain' | 'dry-ice';

/** Субстанция (МНН): родитель для стандартов, примесей, метаболитов и меченых соединений (ТЗ 5.1) */
export interface Substance {
  slug: string;
  nameRu: string;
  nameEn: string;
  cas?: string;
  /** Брутто-формула в порядке Хилла; цифры выводятся тегом sub */
  formula?: string;
  molecularWeight?: string;
  synonyms?: string[];
  /** Описание для страницы субстанции; без текста страница не индексируется */
  description?: string[];
}

export type DocumentType = 'coa' | 'sds' | 'spec' | 'datasheet' | 'manual' | 'certificate' | 'strain-passport' | 'leaflet';

export interface ProductDocument {
  type: DocumentType;
  title: string;
  lang: 'ru' | 'en';
  /** Есть файл — скачивание; нет — «Запросить» (CoA партии всегда по запросу, ТЗ 5.1) */
  href?: string;
}

export interface SpecRow {
  label: string;
  value: string;
}

/** Карточка товара (ТЗ 5.2, 5.4). Пустые необязательные поля на витрине не выводятся. */
export interface ProductDetail extends ProductPreview {
  nameRu?: string;
  synonyms?: string[];
  altCas?: string[];
  formula?: string;
  molecularWeight?: string;
  iupacName?: string;
  purity?: string;
  /** Фармакопейная статья */
  monograph?: string;
  storage?: StorageCondition;
  shipping?: ShippingCondition;
  dangerousGoods?: boolean;
  /** Технические данные типа 2 и 3: колонки, оборудование, штаммы, фармакопеи */
  specs?: SpecRow[];
  /** Уникальное описание (абзацы). Пусто — показываем короткий шаблонный текст, карточка в noindex */
  description: string[];
  /** true — описание написано для этой позиции (проверено химиком), а не собрано по шаблону */
  uniqueDescription: boolean;
  documents: ProductDocument[];
  faq?: { q: string; a: string }[];
  /** Полнота 0–100 (ТЗ 5.6) и итог для индексации (SEO-07) */
  completeness: number;
  indexable: boolean;
  updatedAt: string;
}
