/**
 * Данные страницы категории (только сервер): контент из API, хлебные крошки, навигация по разделам, производители.
 * Третий уровень пути — SEO-посадочная из среза фильтров (ТЗ URL-07): /catalog/chromatography/hplc-columns/waters-c18/.
 */
import type { Locale } from '@/i18n/routing';
import type { Category, FacetKey } from '@/types/catalog';
import type { BreadcrumbItem, CategoryContent, CategoryPageData, SeoLanding } from '@/types/content';
import { getCatalogTree } from './api';
import { apiOrNull } from './backend';
import { countInScope, getCategoryBrands } from './catalog-api';
import { allLandings, findLanding, LANDING_MIN_ITEMS, landingFor, landingHref } from './landings';

interface ApiCategory {
  path: string;
  nameRu: string;
  nameEn?: string | null;
  facets: FacetKey[];
  isIndexed: boolean;
  content: { ru?: CategoryContent; en?: CategoryContent };
  updatedAt: string;
}

/** preview — черновик раздела из админки по подписанной ссылке (без кэша) */
export function getCategory(path: string, preview?: string): Promise<ApiCategory | null> {
  return apiOrNull<ApiCategory>(
    '/public/catalog/category',
    { path, preview },
    preview ? { revalidate: false } : { tags: ['catalog', `category:${path}`] },
  );
}

/** Посадочная индексируется, если в срезе достаточно позиций (иначе это тонкая страница) */
export async function isLandingIndexable(l: Pick<SeoLanding, 'parent' | 'preset'>): Promise<boolean> {
  return (await countInScope(l.parent.split('/'), l.preset)) >= LANDING_MIN_ITEMS;
}

export async function getCategoryPage(
  path: string[],
  locale: Locale,
  labels: { home: string; catalog: string; categories: string },
  preview?: string,
): Promise<(CategoryPageData & { landing?: SeoLanding; hasEn: boolean; preview: boolean }) | null> {
  const found = await findLanding(path, preview);
  const categoryPath = found ? found.parent.split('/') : path;
  if (categoryPath.length > 2) return null;
  const key = categoryPath.join('/');
  const [data, tree] = await Promise.all([getCategory(key, found ? undefined : preview), getCatalogTree(locale)]);
  const ruContent = data?.content.ru;
  if (!data || !ruContent) return null;
  // Набор фильтров — общий для обоих языков, ведётся у раздела
  const facets = data.facets.length ? data.facets : ruContent.facets;
  // Английский текст раздела или посадочной; без перевода страница остаётся русской и закрыта в /en/ (EN-05)
  const enContent = data.content.en ? { ...data.content.en, facets } : undefined;
  const landingEn = found ? landingFor(found, 'en') : undefined;
  const hasEn = !!enContent && (!found || !!landingEn?.hasEn);
  const en = locale === 'en' && hasEn;
  const parentContent = en && enContent ? enContent : { ...ruContent, facets };
  const landing = found ? landingFor(found, en ? 'en' : 'ru') : undefined;

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
  const candidates = (await allLandings()).filter((l) => l.parent === key);
  const indexable = await Promise.all(candidates.map(isLandingIndexable));
  const landingLinks = candidates
    .filter((_, i) => indexable[i])
    .map((l) => ({ label: landingFor(l, en ? 'en' : 'ru').name, href: landingHref(l), active: l.slug === landing?.slug }));

  const brands = (await getCategoryBrands(categoryPath, landing?.preset))
    .filter((b) => b.slug !== 'various')
    .map((b) => ({ ...b, logo: b.logo ?? undefined }));
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
    preview: !!preview,
  };
}
