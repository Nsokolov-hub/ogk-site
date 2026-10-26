/**
 * SEO-посадочные из срезов фильтров (ТЗ URL-07): /catalog/chromatography/hplc-columns/waters-c18/. Их создают и ведут
 * в админке (ADM-07); здесь — чтение из API. Индексируется посадочная с ≥ 3 позициями. Только сервер.
 */
import type { CatalogFilters } from '@/types/catalog';
import type { SeoLanding } from '@/types/content';
import { api, apiOrNull } from './backend';
import { localize, type Localized } from './content';

export const LANDING_MIN_ITEMS = 3;

type LandingText = Omit<SeoLanding, 'parent' | 'slug' | 'preset' | 'updatedAt'> & { updatedAt?: string };

export interface ApiLanding {
  id: string;
  parent: string;
  slug: string;
  preset: CatalogFilters;
  position: number;
  content: Localized<LandingText>;
  updatedAt: string | null;
  preview?: boolean;
}

export const landingHref = (l: { parent: string; slug: string }) => `/catalog/${l.parent}/${l.slug}/`;

/** Все опубликованные посадочные */
export function allLandings(): Promise<ApiLanding[]> {
  return api<ApiLanding[]>('/public/landings', undefined, { tags: ['catalog', 'landings'] });
}

/** Посадочная в форме страницы категории на языке страницы; hasEn — есть ли английский текст (EN-05) */
export function landingFor(row: ApiLanding, locale: string): SeoLanding & { hasEn: boolean } {
  const text = localize(row.content, locale);
  return {
    ...text,
    parent: row.parent,
    slug: row.slug,
    preset: row.preset,
    facets: text.facets ?? [],
    updatedAt: text.updatedAt ?? row.updatedAt ?? '',
  };
}

/** Последний сегмент пути — посадочная внутри раздела; preview — черновик из админки по подписанной ссылке */
export async function findLanding(path: string[], preview?: string): Promise<ApiLanding | null> {
  if (path.length < 2) return null;
  const parent = path.slice(0, -1).join('/');
  const slug = path[path.length - 1];
  if (preview) {
    return apiOrNull<ApiLanding>('/public/landing', { path: parent, slug, preview }, { revalidate: false });
  }
  return (await allLandings()).find((l) => l.parent === parent && l.slug === slug) ?? null;
}
