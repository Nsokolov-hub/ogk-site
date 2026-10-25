'use client';

import { useEffect, useRef } from 'react';
import { usePathname, useSearchParams } from 'next/navigation';
import { CONSENT_EVENT, hasAnalyticsConsent } from '@/lib/consent';
import { counters, type CounterIds } from '@/lib/analytics';

type Queue = ((...args: unknown[]) => void) & { a?: unknown[][]; l?: number };

/**
 * Яндекс Метрика и GA4 (ТЗ 15.1). Загружаются только после согласия на аналитические cookies (NFR-06); номера
 * счётчиков приходят с сервера при запросе страницы, поэтому стейдж и продакшен пишут в разные счётчики одним образом.
 * Вебвизор не записывает ввод в поля: у всех полей форм класс ym-disable-keys (NFR-08).
 */
export function Counters({ ids, nonce }: { ids: CounterIds; nonce?: string }) {
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const loaded = useRef(false);
  const lastHit = useRef('');

  useEffect(() => {
    const load = () => {
      if (loaded.current || !hasAnalyticsConsent() || (!ids.ym && !ids.ga)) return;
      loaded.current = true;
      counters.ids = ids;
      const w = window as unknown as Record<string, unknown>;
      const inject = (src: string) => {
        const script = document.createElement('script');
        script.async = true;
        script.src = src;
        if (nonce) script.nonce = nonce;
        document.head.appendChild(script);
      };
      if (ids.ym) {
        const ym: Queue = (w.ym as Queue) ?? function (...args: unknown[]) {
          (ym.a = ym.a ?? []).push(args);
        };
        ym.l = Date.now();
        w.ym = ym;
        inject('https://mc.yandex.ru/metrika/tag.js');
        ym(ids.ym, 'init', { defer: true, clickmap: true, trackLinks: true, accurateTrackBounce: true, webvisor: true });
      }
      if (ids.ga) {
        const dataLayer = ((w.dataLayer as unknown[]) ?? []) as unknown[];
        w.dataLayer = dataLayer;
        w.gtag = function () {
          // gtag.js читает именно объект arguments
          // eslint-disable-next-line prefer-rest-params
          dataLayer.push(arguments);
        };
        const gtag = w.gtag as (...args: unknown[]) => void;
        gtag('js', new Date());
        gtag('config', ids.ga, { send_page_view: false });
        inject(`https://www.googletagmanager.com/gtag/js?id=${encodeURIComponent(ids.ga)}`);
      }
      lastHit.current = '';
      hit();
    };
    window.addEventListener(CONSENT_EVENT, load);
    load();
    return () => window.removeEventListener(CONSENT_EVENT, load);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [ids.ym, ids.ga, nonce]);

  // Просмотр страницы при каждом переходе внутри сайта: сам переход Next не перезагружает страницу
  const hit = () => {
    if (!loaded.current) return;
    const url = window.location.href;
    if (url === lastHit.current) return;
    lastHit.current = url;
    const w = window as unknown as Record<string, (...args: unknown[]) => void>;
    if (ids.ym && w.ym) w.ym(ids.ym, 'hit', url, { title: document.title });
    if (ids.ga && w.gtag) w.gtag('event', 'page_view', { page_location: url, page_title: document.title });
  };

  useEffect(() => {
    hit();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [pathname, searchParams]);

  return null;
}
