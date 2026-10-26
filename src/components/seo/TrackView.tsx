'use client';

import { useEffect } from 'react';
import { track, type AnalyticsEvent } from '@/lib/analytics';

/**
 * Событие просмотра страницы: product_view, brand_view, service_view (ТЗ 15.2).
 * demandSlug — карточка: просмотр раз за сеанс уходит в API для очереди «обогатить» по спросу (ТЗ 5.6);
 * он не зависит от согласия на cookies — это счётчик карточки, без данных посетителя.
 */
export function TrackView({ event, params, demandSlug }: { event: AnalyticsEvent; params: Record<string, unknown>; demandSlug?: string }) {
  const key = JSON.stringify(params);
  useEffect(() => {
    track(event, JSON.parse(key));
  }, [event, key]);
  useEffect(() => {
    if (!demandSlug) return;
    const seen = `ogk-viewed:${demandSlug}`;
    try {
      if (window.sessionStorage.getItem(seen)) return;
      window.sessionStorage.setItem(seen, '1');
    } catch {
      // без хранилища сеанса просмотр всё равно учитывается
    }
    void fetch(`/api/v1/public/products/${encodeURIComponent(demandSlug)}/view/`, { method: 'POST', keepalive: true }).catch(() => undefined);
  }, [demandSlug]);
  return null;
}
