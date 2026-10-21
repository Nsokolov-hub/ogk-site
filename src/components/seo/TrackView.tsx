'use client';

import { useEffect } from 'react';
import { track, type AnalyticsEvent } from '@/lib/analytics';

/** Событие просмотра страницы: product_view, brand_view, service_view (ТЗ 15.2) */
export function TrackView({ event, params }: { event: AnalyticsEvent; params: Record<string, unknown> }) {
  const key = JSON.stringify(params);
  useEffect(() => {
    track(event, JSON.parse(key));
  }, [event, key]);
  return null;
}
