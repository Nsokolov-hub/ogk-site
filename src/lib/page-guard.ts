/**
 * Разбор ответа API текстов на странице: переехала — 301 на новый адрес (URL-03), нет — 404.
 * Предпросмотр черновика из админки всегда закрыт от индексации.
 */
import type { Metadata } from 'next';
import { notFound, permanentRedirect } from 'next/navigation';
import type { PageResult } from './content';

export function ensurePage<T>(result: PageResult<T>, locale: string): T {
  if (result.moved) permanentRedirect(locale === 'en' ? `/en${result.moved}` : result.moved);
  if (!result.page) notFound();
  return result.page;
}

/** Метаданные предпросмотра: noindex, nofollow — черновик никогда не попадает в поиск */
export function previewMetadata(meta: Metadata, preview: boolean): Metadata {
  return preview ? { ...meta, robots: { index: false, follow: false } } : meta;
}
