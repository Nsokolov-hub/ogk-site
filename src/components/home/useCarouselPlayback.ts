'use client';

import { useEffect, useRef } from 'react';

/** Give readers a full delay after returning to the carousel or releasing the pointer. */
export function useCarouselPlayback(advance: () => void, enabled: boolean, delay: number) {
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const el = ref.current;
    if (!el || !enabled) return;
    const motion = window.matchMedia('(prefers-reduced-motion: reduce)');
    let visible = false;
    let timer: number | undefined;
    const stop = () => window.clearTimeout(timer);
    const start = () => {
      stop();
      if (!visible || document.hidden || motion.matches || el.matches(':hover, :focus-within, :active')) return;
      timer = window.setTimeout(() => { advance(); start(); }, delay);
    };
    const observer = new IntersectionObserver(([entry]) => { visible = entry.isIntersecting; start(); });
    observer.observe(el);
    el.addEventListener('pointerenter', stop);
    el.addEventListener('pointerleave', start);
    el.addEventListener('pointerdown', stop);
    el.addEventListener('pointerup', start);
    el.addEventListener('focusin', stop);
    el.addEventListener('focusout', start);
    motion.addEventListener('change', start);
    document.addEventListener('visibilitychange', start);
    return () => {
      stop();
      observer.disconnect();
      el.removeEventListener('pointerenter', stop);
      el.removeEventListener('pointerleave', start);
      el.removeEventListener('pointerdown', stop);
      el.removeEventListener('pointerup', start);
      el.removeEventListener('focusin', stop);
      el.removeEventListener('focusout', start);
      motion.removeEventListener('change', start);
      document.removeEventListener('visibilitychange', start);
    };
  }, [advance, delay, enabled]);
  return ref;
}
