import type { BrandRef, Category, FacetKey } from './catalog';

/** Контент страницы категории (ТЗ 5.1, 5.5, 10.3). В будущем — из админки. */
export interface CategoryContent {
  h1: string;
  title: string;
  description: string;
  /** Краткое описание под заголовком */
  intro: string;
  /** Полезная информация (SEO-текст), абзацы */
  seoText?: string[];
  /** Условия поставки */
  delivery?: string[];
  faq?: { q: string; a: string }[];
  documents?: { title: string; href: string }[];
  /** Внутренние ссылки: разделы, услуги, статьи */
  related?: { label: string; href: string }[];
  /** Набор фильтров категории */
  facets: FacetKey[];
}

export interface BreadcrumbItem {
  label: string;
  href?: string;
}

export interface CategoryPageData {
  /** null — корень /catalog/ */
  category: Category | null;
  href: string;
  content: CategoryContent;
  breadcrumbs: BreadcrumbItem[];
  /** Блок «Категории» в боковой панели */
  nav: { title: string; parent?: { label: string; href: string }; items: { label: string; href: string; active: boolean }[] };
  /** Производители раздела с числом позиций */
  brands: (BrandRef & { count: number })[];
}

export interface ImageRef {
  src: string;
  alt: string;
  width: number;
  height: number;
}

export interface Cta {
  label: string;
  href: string;
  variant: 'primary' | 'secondary';
  icon?: 'plus' | 'dot' | 'arrow';
}

export interface HeroSlide {
  id: string;
  title: string;
  subtitle: string;
  ctas: Cta[];
  /** cover — фон на весь экран; object — предмет справа на тёмном фоне */
  imageMode: 'cover' | 'object';
  image: ImageRef;
}

/** icon — имя иконки из components/ui/Icon */
export interface IconText {
  id: string;
  title: string;
  text: string;
  icon: string;
}

export interface ServiceItem {
  id: string;
  title: string;
  href: string;
  text: string;
  captionLabel: string;
  chips: { label: string; href?: string }[];
  image: ImageRef;
}

export interface Capability {
  id: string;
  prefix: string;
  accent: string;
  suffix: string;
  href: string;
}

export interface HomeContent {
  hero: {
    slides: HeroSlide[];
    /** Большой поиск под слайдами: главный вход для тех, кто ищет по кат. № и CAS (ТЗ 3) */
    search: { title: string; examples: string[] };
    /** Факты рядом с поиском: только подтверждённые цифры компании */
    facts: { value: string; label: string }[];
  };
  products: { title: string; accent: string; subtitle: string };
  brands: { title: string; accent: string; subtitle: string; items: BrandRef[] };
  promo: { title: string; text: string; cta: Cta; image: ImageRef };
  quality: { title: string; accent: string; subtitle: string; items: IconText[] };
  services: { title: string; accent: string; subtitle: string; items: ServiceItem[] };
  whyUs: { title: string; accent: string; textAccent: string; text: string; items: IconText[] };
  capabilities: { title: string; items: Capability[] };
  request: { title: string; accent: string; promises: IconText[] };
  subscribe: { title: string; accent: string; text: string };
}

/** Общие поля SEO у страниц из админки (ADM-02) */
export interface SeoFields {
  h1: string;
  title: string;
  description: string;
  /** Есть ли перевод на английский (EN-05): без перевода /en/-версия не индексируется */
  hasEn?: boolean;
  updatedAt: string;
}

export interface Faq {
  q: string;
  a: string;
}

export interface LinkItem {
  label: string;
  href: string;
}

/** Страница бренда /brands/{slug}/ (ТЗ 4.1, 5.1) */
export interface BrandContent extends SeoFields {
  slug: string;
  name: string;
  logo?: string;
  /** Страна и город производителя — только подтверждённые данные */
  country?: string;
  /** Короткая строка для списка брендов */
  summary: string;
  intro: string;
  text: string[];
  /** Основные группы товаров со ссылками на разделы каталога */
  groups: LinkItem[];
  /** Позиции этого бренда поставляются в любой фасовке под запрос (ТЗ 5.2.2) */
  customPackaging?: boolean;
  faq?: Faq[];
  /** Очередь из ТЗ 4.2: 1 — первая, 2 — вторая */
  wave: 1 | 2;
}

export type ServiceFieldKind = 'route' | 'temperature' | 'cargo' | 'date' | 'goods' | 'permit' | 'regulator';

/** Страница услуги /services/{slug}/ (ТЗ 4.1, 10.3, SC-06) */
export interface ServiceContent extends SeoFields {
  slug: string;
  /** Короткое название для меню и списков */
  name: string;
  summary: string;
  intro: string;
  /** Что входит в услугу */
  includes: string[];
  /** Как работаем — настоящая последовательность шагов */
  steps: { title: string; text: string }[];
  /** Что понадобится от клиента */
  needs?: string[];
  text?: string[];
  /** Справочная таблица (например, температурные режимы) */
  table?: { caption: string; head: string[]; rows: string[][] };
  /** Страны, откуда доставляем — для логистических услуг */
  countries?: string[];
  faq?: Faq[];
  related: LinkItem[];
  /** Поля формы расчёта (RFQ-08: набор полей задаётся на услугу) */
  form: { title: string; text: string; fields: ServiceFieldKind[] };
  /** Картинка из лендинга, если есть */
  image?: ImageRef;
}

export type ArticleBlock =
  | { type: 'h2'; id: string; text: string }
  | { type: 'p'; text: string }
  | { type: 'ul'; items: string[] }
  | { type: 'table'; caption: string; head: string[]; rows: string[][] }
  | { type: 'note'; text: string };

/** Статья /articles/{slug}/ (ТЗ 10.4) */
export interface Article extends SeoFields {
  slug: string;
  lead: string;
  publishedAt: string;
  authorSlug: string;
  /** Проверено экспертом-химиком (ТЗ 10.4) */
  reviewed: boolean;
  readingMinutes: number;
  body: ArticleBlock[];
  /** Ссылки статья → категория → бренды → услуги (SEO-08) */
  links: LinkItem[];
  cta: { title: string; text: string; href: string; label: string };
}

export interface Author {
  slug: string;
  name: string;
  role: string;
  /** Квалификация и опыт; пока не заполнено — страница автора закрыта от индексации */
  bio?: string[];
  photo?: ImageRef;
}

/** Страницы доверия: /about/, /delivery/, /documents/ (ТЗ 10.4) */
export interface TrustPage extends SeoFields {
  slug: 'about' | 'delivery' | 'documents' | 'contacts';
  intro: string;
}
