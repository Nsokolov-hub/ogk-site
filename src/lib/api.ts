/**
 * Функции данных сайта. Работают и на сервере, и в браузере.
 * Сейчас отдают моки; позже тела заменятся на fetch к /api/v1/public/* — сигнатуры не меняем.
 */
import type { Locale } from '@/i18n/routing';
import type { Category, ProductPreview } from '@/types/catalog';
import type { HomeContent } from '@/types/content';
import type { SiteRequestPayload, SiteRequestResult } from '@/types/requests';
import type { SiteSettings } from '@/types/settings';
import { catalogTree } from '@/data/mock/categories';
import { homeContentRu } from '@/data/mock/home';
import { mockProducts } from '@/data/mock/products';
import { siteSettings } from '@/data/mock/settings';

/** Имитация сети только в браузере, чтобы не тормозить серверный рендер */
async function networkDelay(ms = 300) {
  if (typeof window !== 'undefined') await new Promise((r) => setTimeout(r, ms));
}

export async function getSiteSettings(): Promise<SiteSettings> {
  return siteSettings;
}

export async function getHomeContent(locale: Locale): Promise<HomeContent> {
  void locale; // EN-контент главной добавим вместе с переводами
  return homeContentRu;
}

export async function getCatalogTree(locale: Locale): Promise<Category[]> {
  void locale;
  return catalogTree;
}

export type HomeProductsSort = 'popular' | 'alpha';

const MOCK_TOTAL = 36;

/** Моки повторяются по кругу, чтобы «Загрузить ещё» можно было нажать дважды */
function buildMockList(sort: HomeProductsSort): ProductPreview[] {
  const base = sort === 'alpha' ? [...mockProducts].sort((a, b) => a.name.localeCompare(b.name, 'en')) : mockProducts;
  return Array.from({ length: MOCK_TOTAL }, (_, i) => {
    const p = base[i % base.length];
    const round = Math.floor(i / base.length);
    if (round === 0) return p;
    return {
      ...p,
      id: `${p.id}-r${round}`,
      slug: `${p.slug}-r${round}`,
      packagings: p.packagings.map((pk) => ({ ...pk, id: `${pk.id}-r${round}` })),
    };
  });
}

export async function getHomeProducts(p: {
  sort: HomeProductsSort;
  offset: number;
  limit: number;
  locale: Locale;
}): Promise<{ items: ProductPreview[]; total: number }> {
  await networkDelay();
  const list = buildMockList(p.sort);
  return { items: list.slice(p.offset, p.offset + p.limit), total: list.length };
}

let requestCounter = 122;

export async function submitSiteRequest(p: SiteRequestPayload): Promise<SiteRequestResult> {
  await networkDelay(700);
  if (process.env.NODE_ENV !== 'production') console.debug('[api] submitSiteRequest', p);
  requestCounter += 1;
  return {
    siteRequestId: crypto.randomUUID(),
    number: `S-2026-${String(requestCounter).padStart(6, '0')}`,
  };
}

export async function subscribe(p: {
  email: string;
  personalDataConsent: true;
  marketingConsent: true;
  source: 'home';
}): Promise<{ ok: true }> {
  await networkDelay(500);
  if (process.env.NODE_ENV !== 'production') console.debug('[api] subscribe', p);
  return { ok: true };
}
