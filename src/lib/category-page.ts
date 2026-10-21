/**
 * Данные страницы категории (только сервер): контент, хлебные крошки, навигация по разделам, производители.
 * Отдельный модуль, чтобы тексты категорий не попадали в браузерный бандл.
 */
import type { Locale } from '@/i18n/routing';
import type { Category } from '@/types/catalog';
import type { BreadcrumbItem, CategoryPageData } from '@/types/content';
import { categoryContent } from '@/data/mock/category-content';
import { getCatalogTree } from './api';
import { getCategoryBrands } from './catalog-api';

export async function getCategoryPage(
  path: string[],
  locale: Locale,
  labels: { home: string; catalog: string; categories: string },
): Promise<CategoryPageData | null> {
  if (path.length > 2) return null;
  const content = categoryContent[path.join('/')];
  if (!content) return null;

  const tree = await getCatalogTree(locale);
  const top = path[0] ? tree.find((c) => c.slug === path[0]) : undefined;
  if (path[0] && !top) return null;
  const sub = path[1] ? top?.children?.find((c) => c.slug === path[1]) : undefined;
  if (path[1] && !sub) return null;

  const category: Category | null = sub ?? top ?? null;
  const breadcrumbs: BreadcrumbItem[] = [{ label: labels.home, href: '/' }];
  if (!top) breadcrumbs.push({ label: labels.catalog });
  else {
    breadcrumbs.push({ label: labels.catalog, href: '/catalog/' });
    if (sub) breadcrumbs.push({ label: top.name, href: top.href }, { label: sub.name });
    else breadcrumbs.push({ label: top.name });
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

  const brands = (await getCategoryBrands(path)).filter((b) => b.slug !== 'various');

  return { category, href: category?.href ?? '/catalog/', content, breadcrumbs, nav, brands };
}
