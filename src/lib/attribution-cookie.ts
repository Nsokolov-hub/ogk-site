import type { NextRequest, NextResponse } from 'next/server';

/**
 * Источник визита (ТЗ 15.3): первое касание сохраняется в first-party cookie на 90 дней, последнее обновляется
 * на каждом визите с метками или с внешнего сайта. Cookie читает API при отправке заявки (backend/app/requests/
 * attribution.py), поэтому цепочка «Яндекс → статья → EDQM → товар → заявка через неделю» доходит до CRM.
 * Ставится сервером (middleware), а не скриптом: так она живёт свои 90 дней и в Safari.
 */
export const ATTRIBUTION_COOKIE = 'ogk_attr';
const MAX_AGE = 90 * 24 * 60 * 60;
const PARAMS = ['utm_source', 'utm_medium', 'utm_campaign', 'utm_content', 'utm_term', 'yclid', 'gclid'] as const;
const OWN_HOST = /(^|\.)ogk-chem\.ru$/;
const MAX_COOKIE = 3500;

type Touch = Partial<Record<(typeof PARAMS)[number] | 'landing_url' | 'referrer' | 'at', string>>;

function encode(value: unknown): string {
  const bytes = new TextEncoder().encode(JSON.stringify(value));
  let binary = '';
  bytes.forEach((b) => (binary += String.fromCharCode(b)));
  return btoa(binary).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');
}

function decode(raw: string | undefined): { first?: Touch; last?: Touch } | null {
  if (!raw) return null;
  try {
    const binary = atob(raw.replace(/-/g, '+').replace(/_/g, '/'));
    const json = new TextDecoder().decode(Uint8Array.from(binary, (c) => c.charCodeAt(0)));
    const data = JSON.parse(json);
    return data && typeof data === 'object' ? data : null;
  } catch {
    return null;
  }
}

function externalReferrer(request: NextRequest): string | undefined {
  const referrer = request.headers.get('referer');
  if (!referrer) return undefined;
  try {
    const host = new URL(referrer).hostname;
    return OWN_HOST.test(host) || host === request.nextUrl.hostname ? undefined : referrer.slice(0, 500);
  } catch {
    return undefined;
  }
}

/** Только переходы на страницы: без предзагрузки ссылок, RSC-запросов и фоновых fetch */
function isPageVisit(request: NextRequest): boolean {
  if (request.method !== 'GET') return false;
  const h = request.headers;
  if (h.get('next-router-prefetch') || h.get('rsc') || h.get('purpose') === 'prefetch' || h.get('sec-purpose')?.includes('prefetch')) return false;
  const dest = h.get('sec-fetch-dest');
  return dest ? dest === 'document' : (h.get('accept') ?? '').includes('text/html');
}

export function trackAttribution(request: NextRequest, response: NextResponse): void {
  if (!isPageVisit(request)) return;
  const params = request.nextUrl.searchParams;
  const referrer = externalReferrer(request);
  const marked = PARAMS.some((key) => params.get(key));
  const stored = decode(request.cookies.get(ATTRIBUTION_COOKIE)?.value);
  if (stored?.first && !marked && !referrer) return;

  const url = new URL(request.nextUrl.href);
  url.hash = '';
  const touch: Touch = { landing_url: url.toString().slice(0, 500), at: new Date().toISOString() };
  if (referrer) touch.referrer = referrer;
  for (const key of PARAMS) {
    const value = params.get(key);
    if (value) touch[key] = value.slice(0, 200);
  }
  let value = encode({ first: stored?.first ?? touch, last: touch });
  if (value.length > MAX_COOKIE) value = encode({ first: stored?.first ?? touch, last: { ...touch, landing_url: touch.landing_url?.split('?')[0], referrer: undefined } });
  if (value.length > MAX_COOKIE) return;
  response.cookies.set(ATTRIBUTION_COOKIE, value, {
    path: '/',
    maxAge: MAX_AGE,
    httpOnly: true,
    sameSite: 'lax',
    // Только по HTTPS, если сайт открыт по HTTPS (в том числе за прокси); по http://localhost cookie тоже живёт
    secure: request.nextUrl.protocol === 'https:' || request.headers.get('x-forwarded-proto') === 'https',
  });
}
