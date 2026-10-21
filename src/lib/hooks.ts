'use client';

import { useCallback, useRef, useSyncExternalStore } from 'react';
import { track } from './analytics';

const REDUCED_MOTION_QUERY = '(prefers-reduced-motion: reduce)';

/** true, если пользователь просит меньше анимации */
export function usePrefersReducedMotion(): boolean {
  return useSyncExternalStore(
    (cb) => {
      const mq = window.matchMedia(REDUCED_MOTION_QUERY);
      mq.addEventListener('change', cb);
      return () => mq.removeEventListener('change', cb);
    },
    () => window.matchMedia(REDUCED_MOTION_QUERY).matches,
    () => false,
  );
}

/**
 * Служебные данные формы: событие form_start при первом фокусе
 * и время заполнения для антиспама (RFQ-06).
 */
export function useFormMeta(formType: string) {
  const started = useRef(false);
  const mountedAt = useRef<number | null>(null);

  const onFocusCapture = useCallback(() => {
    if (mountedAt.current === null) mountedAt.current = Date.now();
    if (started.current) return;
    started.current = true;
    track('form_start', { form_type: formType });
  }, [formType]);

  const elapsedMs = useCallback(() => (mountedAt.current === null ? 0 : Date.now() - mountedAt.current), []);

  return { onFocusCapture, elapsedMs };
}
