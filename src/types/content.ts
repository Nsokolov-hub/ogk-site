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
