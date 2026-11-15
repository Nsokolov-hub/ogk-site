import { CONSENT_EVENT, hasAnalyticsConsent } from './consent';

/** Номера счётчиков: Метрика — число, GA4 — G-XXXXXXX. Пустые — счётчик выключен */
export interface CounterIds {
  ym: number | null;
  ga: string | null;
}

/** Счётчики, загруженные после согласия (components/analytics/Counters) */
export const counters: { ids: CounterIds | null } = { ids: null };

/** События ТЗ 15.2: в dataLayer, цели Метрики (reachGoal) и события GA4 — одним вызовом */
export type AnalyticsEvent =
  | 'form_start'
  | 'form_submit'
  | 'lead_submit'
  | 'form_attempt'
  | 'form_error'
  | 'request_open'
  | 'quote_request'
  | 'product_request'
  | 'add_to_rfq'
  | 'click_phone'
  | 'click_email'
  | 'download_document'
  | 'site_search'
  | 'search_suggest'
  | 'search_submit'
  | 'search_result_click'
  | 'search_no_results'
  | 'catalog_filter'
  | 'product_view'
  | 'brand_view'
  | 'service_view'
  | 'subscribe'
  | 'bulk_upload';

type PendingEvent = { event: AnalyticsEvent; params: Record<string, unknown> };
const pending: PendingEvent[] = [];
const leads = new Set<string>();

/** Return links carry bearer tokens; none of their query/fragment/path secrets belong in analytics. */
export function sanitizeAnalyticsUrl(value: string): string {
  try {
    const base = typeof window === 'undefined' ? 'https://www.ogk-chem.ru' : window.location.origin;
    const url = new URL(value, base);
    url.hash = '';
    for (const key of [...url.searchParams.keys()])
      if (/^(repeat|code)$|token|secret|password|signature/i.test(key)) url.searchParams.delete(key);
    url.pathname = url.pathname.replace(/(\/public\/requests\/repeat\/)[^/]+/i, '$1redacted');
    return /^[a-z][a-z\d+.-]*:/i.test(value) ? url.toString() : `${url.pathname}${url.search}`;
  } catch {
    return value.split(/[?#]/)[0];
  }
}

function safeParams(params: Record<string, unknown>): Record<string, unknown> {
  return Object.fromEntries(Object.entries(params).filter(([key]) => !/^repeat$|token|secret|password|signature/i.test(key))
    .map(([key, value]) => [key, typeof value === 'string' && /(^|_)(page|url|href|destination|referrer)$/i.test(key)
      ? sanitizeAnalyticsUrl(value)
      : Array.isArray(value) ? value.map((item) => item && typeof item === 'object' ? safeParams(item as Record<string, unknown>) : item)
        : value && typeof value === 'object' ? safeParams(value as Record<string, unknown>) : value]));
}

function emit(event: AnalyticsEvent, params: Record<string, unknown>, ids: CounterIds): void {
  const w = window as unknown as Record<string, ((...args: unknown[]) => void) | undefined>;
  if (ids.ym && w.ym) w.ym(ids.ym, 'reachGoal', event, params);
  if (ids.ga && w.gtag) w.gtag('event', event, params);
}

/** A consented event may arrive before Counters has installed the counter's queue. */
export function configureCounters(ids: CounterIds | null): void {
  counters.ids = ids;
  if (!hasAnalyticsConsent()) {
    pending.length = 0;
    return;
  }
  if (!ids) return;
  for (const item of pending.splice(0)) emit(item.event, item.params, ids);
}

/** View events on the current page are measured when consent is granted, never before it. */
export function afterAnalyticsConsent(callback: () => void): () => void {
  if (typeof window === 'undefined') return () => undefined;
  let sent = false;
  const run = () => {
    if (sent || !hasAnalyticsConsent()) return;
    sent = true;
    callback();
  };
  window.addEventListener(CONSENT_EVENT, run);
  run();
  return () => window.removeEventListener(CONSENT_EVENT, run);
}

declare global {
  interface Window {
    dataLayer?: Record<string, unknown>[];
  }
}

export function track(event: AnalyticsEvent, params: Record<string, unknown> = {}): boolean {
  if (typeof window === 'undefined') return false;
  params = safeParams(params);
  const payload = { event, ...params };
  if (process.env.NODE_ENV !== 'production') console.debug('[analytics]', payload);
  if (!hasAnalyticsConsent()) return false;
  window.dataLayer = window.dataLayer ?? [];
  window.dataLayer.push(payload);
  const ids = counters.ids;
  if (ids) emit(event, params, ids);
  else {
    pending.push({ event, params });
    if (pending.length > 100) pending.shift();
  }
  return true;
}

/** Commercial request saved by the API, once per request; newsletter/honeypot successes are not leads. */
export function trackLeadSubmit(formType: string, params: Record<string, unknown>): boolean {
  const id = typeof params.request_id === 'string' ? params.request_id.trim() : '';
  if (!id || formType === 'subscribe' || leads.has(id)) return false;
  if (!track('lead_submit', { ...params, form_type: formType })) return false;
  leads.add(id);
  if (leads.size > 1000) leads.delete(leads.values().next().value!);
  return true;
}
