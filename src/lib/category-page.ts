/**
 * Данные страницы категории (только сервер): контент, хлебные крошки, навигация по разделам, производители.
 * Отдельный модуль, чтобы тексты категорий не попадали в браузерный бандл.
 * Третий уровень пути — SEO-посадочная из среза фильтров (ТЗ URL-07): /catalog/chromatography/hplc-columns/waters-c18/.
 */
import type { Locale } from '@/i18n/routing';
import type { Category, FacetKey } from '@/types/catalog';
import type { BreadcrumbItem, CategoryPageData, SeoLanding } from '@/types/content';
import { categoryContent } from '@/data/mock/category-content';
import { categoryContentEn, landingTextEn } from '@/data/mock/en/category-content';
import { findLanding, LANDING_MIN_ITEMS, landingHref, landings } from '@/data/mock/landings';
import { getCatalogTree } from './api';
import { countInScope, getCategoryBrands } from './catalog-api';

/** Посадочная индексируется, если в срезе достаточно позиций (иначе это тонкая страница) */
export function isLandingIndexable(l: SeoLanding) {
  return countInScope(l.parent.split('/'), l.preset) >= LANDING_MIN_ITEMS;
}

export async function getCategoryPage(
  path: string[],
  locale: Locale,
  labels: { home: string; catalog: string; categories: string },
): Promise<(CategoryPageData & { landing?: SeoLanding; hasEn: boolean }) | null> {
  const found = findLanding(path);
  const categoryPath = found ? found.parent.split('/') : path;
  if (categoryPath.length > 2) return null;
  const key = categoryPath.join('/');
  const ruContent = categoryContent[key];
  if (!ruContent) return null;
  // Английский текст раздела или посадочной; без перевода страница остаётся русской и закрыта в /en/ (EN-05)
  const enContent = categoryContentEn[key];
  const enLanding = found ? landingTextEn[found.slug] : undefined;
  const hasEn = !!enContent && (!found || !!enLanding);
  const en = locale === 'en' && hasEn;
  const parentContent = en ? enContent : ruContent;
  const landing = found && en ? { ...found, ...enLanding } : found;

  const tree = await getCatalogTree(locale);
  const top = categoryPath[0] ? tree.find((c) => c.slug === categoryPath[0]) : undefined;
  if (categoryPath[0] && !top) return null;
  const sub = categoryPath[1] ? top?.children?.find((c) => c.slug === categoryPath[1]) : undefined;
  if (categoryPath[1] && !sub) return null;

  const category: Category | null = sub ?? top ?? null;
  const breadcrumbs: BreadcrumbItem[] = [{ label: labels.home, href: '/' }];
  if (!top) breadcrumbs.push({ label: labels.catalog });
  else {
    breadcrumbs.push({ label: labels.catalog, href: '/catalog/' });
    const chain = sub ? [top, sub] : [top];
    chain.forEach((c, i) => {
      const last = i === chain.length - 1 && !landing;
      breadcrumbs.push(last ? { label: c.name } : { label: c.name, href: c.href });
    });
    if (landing) breadcrumbs.push({ label: landing.h1 });
  }

  // Навигация: в корне — разделы; в разделе с подразделами — его подразделы; иначе — соседи
  let nav: CategoryPageData['nav'];
  if (top?.children?.length) {
    nav = {
      title: top.name,
      parent: { label: labels.catalog, href: '/catalog/' },
      items: top.children.map((c) => ({ label: c.name, href: c.href, active: c.slug === sub?.slug })),
    };
  } else {
    nav = {
      title: labels.categories,
      items: tree.map((c) => ({ label: c.name, href: c.href, active: c.slug === top?.slug })),
    };
  }

  // Подборки: на категории — её посадочные, на посадочной — соседние (перелинковка, SEO-08)
  const parentKey = categoryPath.join('/');
  const landingLinks = landings
    .filter((l) => l.parent === parentKey && isLandingIndexable(l))
    .map((l) => ({ label: (en ? landingTextEn[l.slug]?.name : undefined) ?? l.name, href: landingHref(l), active: l.slug === landing?.slug }));

  const brands = (await getCategoryBrands(categoryPath, landing?.preset)).filter((b) => b.slug !== 'various');
  // У посадочной фильтры среза зафиксированы — в панели остаются только остальные
  const presetKeys = new Set(Object.keys(landing?.preset ?? {}) as FacetKey[]);
  const content = landing ? { ...landing, facets: landing.facets.filter((f) => !presetKeys.has(f)) } : parentContent;

  return {
    category,
    href: landing ? landingHref(landing) : (category?.href ?? '/catalog/'),
    content,
    breadcrumbs,
    nav,
    brands,
    preset: landing?.preset,
    landings: landingLinks,
    landing,
    hasEn,
  };
}
