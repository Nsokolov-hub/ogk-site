/**
 * Функции данных сайта. Работают и на сервере, и в браузере.
 * Каталог и заявки — API сайта (backend/); настройки и тексты главной пока в коде, до админки (ADM-02, ADM-10).
 */
import type { Locale } from '@/i18n/routing';
import type { Category, ProductPreview } from '@/types/catalog';
import type { HomeContent } from '@/types/content';
import type { SiteRequestPayload, SiteRequestResult } from '@/types/requests';
import type { SiteSettings } from '@/types/settings';
import { homeContentEn } from '@/data/mock/en/home';
import { homeContentRu } from '@/data/mock/home';
import { siteSettings, siteSettingsEn } from '@/data/mock/settings';
import type { Schemas } from './api-types';
import { api } from './backend';
import { requestCaptcha } from './captcha-store';
import { SubmitError } from './submit-error';

/** Имитация сети только в браузере, чтобы не тормозить серверный рендер */
async function networkDelay(ms = 300) {
  if (typeof window !== 'undefined') await new Promise((r) => setTimeout(r, ms));
}

export async function getSiteSettings(locale: Locale = 'ru'): Promise<SiteSettings> {
  return locale === 'en' ? siteSettingsEn : siteSettings;
}

export async function getHomeContent(locale: Locale): Promise<HomeContent> {
  return locale === 'en' ? homeContentEn : homeContentRu;
}

type ApiCategoryNode = Schemas['CategoryNode'];

/** Дерево каталога (ТЗ 4.2) на языке страницы; short — короткое название для кнопок главной и 404 */
export async function getCatalogTree(locale: Locale): Promise<Category[]> {
  const nodes = await api<ApiCategoryNode[]>('/public/catalog/tree', undefined, { tags: ['catalog'] });
  const map = (n: ApiCategoryNode): Category => ({
    slug: n.slug,
    name: locale === 'en' ? (n.nameEn ?? n.nameRu) : n.nameRu,
    short: (locale === 'en' ? n.shortEn : n.shortRu) ?? undefined,
    href: `/catalog/${n.path}/`,
    children: n.children?.length ? n.children.map(map) : undefined,
  });
  return nodes.map(map);
}

export type HomeProductsSort = 'popular' | 'alpha';

/** «Популярные» — самые популярные позиции каталога (подборку можно будет задать в админке) */
export async function getHomeProducts(p: {
  sort: HomeProductsSort;
  offset: number;
  limit: number;
  locale: Locale;
}): Promise<{ items: ProductPreview[]; total: number }> {
  try {
    const page = await api<Schemas['ProductsPage']>('/public/catalog/popular', { lang: p.locale, sort: p.sort, offset: p.offset, limit: p.limit }, { tags: ['catalog'] });
    return page as { items: ProductPreview[]; total: number };
  } catch (error) {
    // Главная открывается и без блока товаров: поиск перезапускается или каталог ещё не загружен
    if (typeof window === 'undefined') return { items: [], total: 0 };
    throw error;
  }
}

// ── заявки: POST /api/v1/public/requests/ (backend/app/requests) ──

const REQUESTS_URL = '/api/v1/public/requests/';
/** Ключ повторяемости живёт 30 минут: повтор той же формы после сбоя сети вернёт ту же заявку, а не вторую */
const KEY_TTL_MS = 30 * 60 * 1000;
const submitKeys = new Map<string, { key: string; at: number }>();

async function contentDigest(p: SiteRequestPayload): Promise<string> {
  // Ловушка и время заполнения отличаются между двумя нажатиями одной отправки, содержание — нет
  const content: Record<string, unknown> = { ...p };
  delete content.attachment;
  delete content.antispam;
  delete content.captchaToken;
  const attachment = p.attachment;
  const file = attachment ? `${attachment.name}:${attachment.size}:${attachment.lastModified}` : '';
  const data = new TextEncoder().encode(JSON.stringify(content) + file);
  const hash = await crypto.subtle.digest('SHA-256', data);
  return Array.from(new Uint8Array(hash), (b) => b.toString(16).padStart(2, '0')).join('');
}

async function idempotencyKey(p: SiteRequestPayload): Promise<{ digest: string; key: string }> {
  const digest = await contentDigest(p);
  const now = Date.now();
  const known = submitKeys.get(digest);
  if (known && now - known.at < KEY_TTL_MS) return { digest, key: known.key };
  const key = crypto.randomUUID();
  submitKeys.set(digest, { key, at: now });
  return { digest, key };
}

let mockCounter = 122;

/**
 * Отправка любой формы. Заявка сохраняется на сервере до ответа (NFR-03), дальше сервер сам доставит её в CRM
 * и разошлёт письма. На 428 открывается SmartCaptcha, и форма уходит повторно с токеном.
 * NEXT_PUBLIC_API_MOCK=1 — вёрстка без бэкенда: номер выдумывается в браузере.
 */
export async function submitSiteRequest(p: SiteRequestPayload): Promise<SiteRequestResult> {
  if (process.env.NEXT_PUBLIC_API_MOCK === '1') {
    await networkDelay(700);
    mockCounter += 1;
    return { siteRequestId: crypto.randomUUID(), number: `S-2026-${String(mockCounter).padStart(6, '0')}` };
  }
  const { attachment, ...body } = p;
  const { digest, key } = await idempotencyKey(p);
  let captchaToken: string | undefined;
  for (let attempt = 0; attempt < 2; attempt += 1) {
    const form = new FormData();
    form.append('payload', JSON.stringify(captchaToken ? { ...body, captchaToken } : body));
    if (attachment) form.append('attachment', attachment);
    let response: Response;
    try {
      response = await fetch(REQUESTS_URL, { method: 'POST', body: form, headers: { 'Idempotency-Key': key }, credentials: 'same-origin' });
    } catch {
      throw new SubmitError('NETWORK', 0);
    }
    const data = await response.json().catch(() => ({}));
    if (response.ok && typeof data.number === 'string') {
      submitKeys.delete(digest);
      return { siteRequestId: data.siteRequestId, number: data.number };
    }
    if (response.status === 428 && data.code === 'CAPTCHA_REQUIRED' && attempt === 0) {
      captchaToken = await requestCaptcha(p.lang);
      continue;
    }
    throw new SubmitError(typeof data.code === 'string' ? data.code : `HTTP_${response.status}`, response.status, Array.isArray(data.fields) ? data.fields : []);
  }
  throw new SubmitError('CAPTCHA_FAILED', 428);
}

/** Подписка на рассылку (ТЗ 11.2, NFR-07): адрес и оба согласия сохраняются в API сайта и уходят в CRM */
export async function subscribe(p: {
  email: string;
  personalDataConsent: true;
  marketingConsent: true;
  lang: Locale;
  source: string;
  pageUrl?: string;
}): Promise<{ ok: true }> {
  if (process.env.NEXT_PUBLIC_API_MOCK === '1') {
    await networkDelay(500);
    return { ok: true };
  }
  await api('/public/subscriptions', undefined, { method: 'POST', body: p, revalidate: false });
  return { ok: true };
}

/** Отписка по ссылке из письма: ответ одинаковый для любого ключа */
export async function unsubscribe(token: string): Promise<void> {
  await api('/public/subscriptions/unsubscribe', undefined, { method: 'POST', body: { token }, revalidate: false });
}
