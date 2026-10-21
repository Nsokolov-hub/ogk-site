import type { BrandRef } from './catalog';

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
    badges: { trust: string; trustAccent: string; makers: string; makersAccent: string };
    slides: HeroSlide[];
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
