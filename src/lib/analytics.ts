import { hasAnalyticsConsent } from './consent';

/** События ТЗ 15.2. Счётчики Метрики и GA4 подключим отдельно — здесь только единый слой событий. */
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
}
