/**
 * Меню «Меню» в шапке (правки дизайна 02.11.2026): пять направлений — каталог, услуги, статьи, о компании, контакты;
 * у каждого свои подразделы. Собирается на сервере из каталога и контента, в шапку и мобильное меню идёт готовым.
 */
import { getTranslations } from 'next-intl/server';
import type { Category } from '@/types/catalog';
import { getArticles, getServices } from './content-api';

export type MenuKey = 'catalog' | 'services' | 'articles' | 'about' | 'contacts';

export interface MenuLink {
  label: string;
  href: string;
}

export interface MenuSection {
  key: MenuKey;
  label: string;
  href: string;
  items: MenuLink[];
  /** Ссылка внизу колонки: весь каталог, все услуги, все статьи */
  all?: MenuLink;
}

const ARTICLES_IN_MENU = 6;

export async function siteMenu(locale: string, tree: Category[]): Promise<MenuSection[]> {
  const t = await getTranslations({ locale, namespace: 'siteMenu' });
  const [services, articles] = await Promise.all([
    getServices(locale).catch((): Awaited<ReturnType<typeof getServices>> => []),
    getArticles(locale).catch((): Awaited<ReturnType<typeof getArticles>> => []),
  ]);
  // На английской версии — только страницы с переводом (EN-05)
  const translated = <T extends { hasEn?: boolean }>(rows: T[]) => (locale === 'en' ? rows.filter((r) => r.hasEn) : rows);

  return [
    {
      key: 'catalog',
      label: t('catalog'),
      href: '/catalog/',
      items: [
        ...tree.map((c) => ({ label: c.name, href: c.href })),
        { label: t('brands'), href: '/brands/' },
        { label: t('substances'), href: '/substances/' },
        { label: t('cas'), href: '/cas/' },
      ],
      all: { label: t('allCatalog'), href: '/catalog/' },
    },
    {
      key: 'services',
      label: t('services'),
      href: '/services/',
      items: [
        ...translated(services).map((s) => ({ label: s.name, href: `/services/${s.slug}/` })),
        { label: t('solutions'), href: '/solutions/' },
      ],
      all: { label: t('allServices'), href: '/services/' },
    },
    {
      key: 'articles',
      label: t('articles'),
      href: '/articles/',
      items: translated(articles)
        .slice(0, ARTICLES_IN_MENU)
        .map((a) => ({ label: a.h1, href: `/articles/${a.slug}/` })),
      all: { label: t('allArticles'), href: '/articles/' },
    },
    {
      key: 'about',
      label: t('about'),
      href: '/about/',
      items: [
        { label: t('aboutPage'), href: '/about/' },
        { label: t('delivery'), href: '/delivery/' },
        { label: t('documents'), href: '/documents/' },
        { label: t('brands'), href: '/brands/' },
      ],
    },
    {
      key: 'contacts',
      label: t('contacts'),
      href: '/contacts/',
      items: [
        { label: t('contactsPage'), href: '/contacts/' },
        { label: t('requisites'), href: '/documents/' },
        { label: t('order'), href: '/rfq/' },
      ],
    },
  ];
}
