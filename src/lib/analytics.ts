import { hasAnalyticsConsent } from './consent';

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
  | 'quote_request'
  | 'product_request'
  | 'add_to_rfq'
  | 'click_phone'
  | 'click_email'
  | 'download_document'
  | 'site_search'
  | 'search_no_results'
  | 'catalog_filter'
  | 'product_view'
  | 'brand_view'
  | 'service_view'
  | 'subscribe'
  | 'bulk_upload';

declare global {
  interface Window {
    dataLayer?: Record<string, unknown>[];
  }
}

export function track(event: AnalyticsEvent, params: Record<string, unknown> = {}): void {
  if (typeof window === 'undefined') return;
  const payload = { event, ...params };
  if (process.env.NODE_ENV !== 'production') console.debug('[analytics]', payload);
  if (!hasAnalyticsConsent()) return;
  window.dataLayer = window.dataLayer ?? [];
  window.dataLayer.push(payload);
  const w = window as unknown as Record<string, ((...args: unknown[]) => void) | undefined>;
  const ids = counters.ids;
  if (ids?.ym && w.ym) w.ym(ids.ym, 'reachGoal', event, params);
  if (ids?.ga && w.gtag) w.gtag('event', event, params);
}
