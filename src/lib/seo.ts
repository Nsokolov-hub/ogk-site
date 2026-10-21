import type { Metadata } from 'next';
import type { Locale } from '@/i18n/routing';

/**
 * SEO-слой: canonical, hreflang и robots для всех страниц по одним правилам (ТЗ 4.3, 4.4, 10.1).
 *
 * - canonical — на себя внутри языка и без query: UTM и служебные параметры его не меняют (URL-09, EN-02);
 * - hreflang ru / en / x-default — только у пары страниц, где есть перевод (EN-02);
 * - EN-страница без перевода: noindex, follow и canonical на русскую версию — полуанглийских страниц
 *   в индексе нет, а переключатель языка всё равно ведёт на ту же страницу (EN-03, EN-05);
 * - index: false — noindex, follow (SEO-07 для товаров с низкой полнотой, служебные страницы).
 */

export const SITE_URL = 'https://www.ogk-chem.ru';
export const SITE_NAME = 'ОГК-ХИМ';

export function localizedPath(locale: Locale | string, path: string) {
  return locale === 'ru' ? path : `/${locale}${path}`;
}

export function absoluteUrl(locale: Locale | string, path: string) {
  return `${SITE_URL}${localizedPath(locale, path)}`;
}

export function pageMetadata(p: {
  locale: Locale;
  /** Путь без локали и query, со слешем на конце: /product/edqm-y0001897-oxcarbazepine-crs/ */
  path: string;
  title: string;
  description: string;
  /** Есть перевод на английский */
  hasEn?: boolean;
  /** false — noindex, follow */
  index?: boolean;
  /** Query, который входит в canonical (только ?page=N, URL-08) */
  canonicalQuery?: string;
  ogType?: 'website' | 'article';
  image?: { url: string; width: number; height: number };
  /** Для статей: даты публикации и обновления в Open Graph */
  article?: { publishedTime: string; modifiedTime: string; authors: string[] };
}): Metadata {
  const { locale, path, hasEn = false, index = true } = p;
  const untranslated = locale !== 'ru' && !hasEn;
  const canonicalLocale = untranslated ? 'ru' : locale;
  const canonical = `${localizedPath(canonicalLocale, path)}${p.canonicalQuery ? `?${p.canonicalQuery}` : ''}`;
  const noindex = !index || untranslated;

  return {
    title: p.title,
    description: p.description,
    alternates: {
      canonical,
      languages: hasEn ? { ru: path, en: `/en${path}`, 'x-default': path } : undefined,
    },
    robots: noindex ? { index: false, follow: true } : undefined,
    openGraph: {
      type: p.ogType ?? 'website',
      url: canonical,
      siteName: SITE_NAME,
      title: p.title,
      description: p.description,
      locale: locale === 'ru' ? 'ru_RU' : 'en_US',
      images: p.image ? [p.image] : [{ url: '/images/home/hero-1.jpg', width: 2880, height: 1728 }],
      ...(p.article
        ? { publishedTime: p.article.publishedTime, modifiedTime: p.article.modifiedTime, authors: p.article.authors }
        : {}),
    },
  };
}

/** Служебные страницы (корзина, поиск, кабинет): noindex, follow; в robots.txt они закрыты (SEO-03) */
export function serviceMetadata(title: string): Metadata {
  return { title, robots: { index: false, follow: true } };
}
