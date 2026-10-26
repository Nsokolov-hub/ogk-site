/**
 * Тексты сайта из API (ADM-02, ADM-10): главная, услуги, решения, статьи, авторы, страницы доверия, контакты и
 * реквизиты. Их ведут в админке; публикация сбрасывает кэш по тегу content. Только сервер.
 *
 * preview — подписанная ссылка предпросмотра из админки: показывает черновик именно этой страницы, без кэша.
 */
import type { Locale } from '@/i18n/routing';
import type { SiteSettings } from '@/types/settings';
import { api, apiOrNull } from './backend';

export type Localized<T> = { ru: T; en?: T };
export type PageKind = 'home' | 'service' | 'solution' | 'article' | 'author' | 'trust';
export type WithEn<T> = T & { hasEn: boolean };

interface ApiPage<T> {
  kind: PageKind;
  slug: string;
  position: number;
  content: Localized<T>;
  updatedAt: string | null;
  preview?: boolean;
  moved?: string;
}

/** Версия на языке страницы; без перевода — русская с hasEn = false: такая /en/-страница в noindex (EN-05) */
export function localize<T extends object>(content: Localized<T>, locale: string): WithEn<T> {
  const en = content.en && Object.keys(content.en).length ? content.en : undefined;
  if (locale === 'en') return en ? { ...content.ru, ...en, hasEn: true } : { ...content.ru, hasEn: false };
  return { ...content.ru, hasEn: !!en };
}

/** Опубликованные страницы одного вида, по порядку из админки */
export async function pageList<T extends object>(kind: PageKind, locale: string): Promise<WithEn<T>[]> {
  const rows = await api<ApiPage<T>[]>('/public/pages', { kind }, { tags: ['content', `pages:${kind}`] });
  return rows.map((row) => localize(row.content, locale));
}

export interface PageResult<T> {
  page: WithEn<T> | null;
  /** Адрес, на который страница переехала (смена адреса в админке, URL-03) */
  moved: string | null;
  preview: boolean;
}

export async function pageContent<T extends object>(kind: PageKind, slug: string, locale: string, preview?: string): Promise<PageResult<T>> {
  const row = await apiOrNull<ApiPage<T>>(
    `/public/pages/${kind}/${encodeURIComponent(slug)}`,
    { preview },
    preview ? { revalidate: false } : { tags: ['content', `page:${kind}:${slug}`] },
  );
  if (!row) return { page: null, moved: null, preview: false };
  if (row.moved) return { page: null, moved: row.moved, preview: false };
  return { page: localize(row.content, locale), moved: null, preview: !!row.preview };
}

/** Мета-шаблоны карточек и субстанций (SEO-02): пустые — витрина берёт свои из messages */
export interface MetaTemplates {
  product: Record<'ru' | 'en', { title?: string; titleNoCas?: string; description?: string }>;
  substance: Record<'ru' | 'en', { title?: string; description?: string }>;
}

export interface SiteData {
  ru: SiteSettings;
  en: SiteSettings;
  counters: { ym: number | null; ga: string | null };
  metaTemplates: MetaTemplates;
  robotsExtra: string;
}

export async function getSite(): Promise<SiteData> {
  return api<SiteData>('/public/site', undefined, { tags: ['content'] });
}

/** Контакты и реквизиты на языке страницы — один источник для шапки, подвала и Organization (ADM-10) */
export async function siteSettingsFor(locale: Locale): Promise<SiteSettings> {
  const site = await getSite();
  return locale === 'en' ? site.en ?? site.ru : site.ru;
}

/** {name} — {brand} {number} → значения; незнакомые плейсхолдеры остаются как есть */
export function fillTemplate(template: string, values: Record<string, string | number | undefined | null>): string {
  return template
    .replace(/\{(\w+)\}/g, (all, key: string) => (values[key] === undefined || values[key] === null ? all : String(values[key])))
    .replace(/\s+([,.|])/g, '$1')
    .replace(/\s{2,}/g, ' ')
    .trim();
}

/** Ссылка предпросмотра из админки в параметрах страницы */
export function previewParam(value: string | string[] | undefined): string | undefined {
  const token = Array.isArray(value) ? value[0] : value;
  return token && token.length <= 500 ? token : undefined;
}
