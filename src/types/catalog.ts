/** «В наличии» | «Под заказ» */
export type Availability = 'in_stock' | 'on_request';

/** Три типа карточек (ТЗ 5.2): стандарты и реактивы / оборудование и колонки / прочее */
export type CardType = 'standard' | 'equipment' | 'other';

export type PackUnit = 'mg' | 'g' | 'ml' | 'pcs';

export interface Packaging {
  id: string;
  /** «100 мг», «1 л», «1 шт.» */
  label: string;
  /** Свой кат. № фасовки, если есть */
  catalogNumber?: string;
  availability: Availability;
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
  /** Сводный статус */
  availability: Availability;
  image?: { src: string; alt: string; kind: 'photo' | 'structure' };
  discontinued?: boolean;
}

export interface Category {
  slug: string;
  name: string;
  /** /catalog/reference-standards/edqm/ */
  href: string;
  children?: Category[];
}
