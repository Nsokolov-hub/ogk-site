'use client';

import type { ComponentProps } from 'react';
import { track, type AnalyticsEvent } from '@/lib/analytics';

/** Ссылка tel:/mailto: с событием аналитики (click_phone, click_email) */
export function TrackedLink({
  event,
  params,
  onClick,
  ...rest
}: ComponentProps<'a'> & { event: AnalyticsEvent; params?: Record<string, unknown> }) {
  return (
    <a
      {...rest}
      onClick={(e) => {
        track(event, params);
        onClick?.(e);
      }}
    />
  );
}
