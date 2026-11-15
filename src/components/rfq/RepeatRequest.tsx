'use client';

import { useEffect, useRef, useState } from 'react';
import { useTranslations } from 'next-intl';
import type { SiteRequestItem } from '@/types/requests';
import { Button } from '@/components/ui/Button';
import { track } from '@/lib/analytics';
import { useRfqStore } from '@/lib/rfq-store';
import { FormStatus } from '@/components/forms/FormStatus';

/** A bearer link restores product choices only after an explicit review, preserving the current cart. */
export function RepeatRequest() {
  const t = useTranslations('rfq.repeat');
  const tu = useTranslations('oneClick.units');
  const token = useRef<string | null>(null);
  const [state, setState] = useState<'idle' | 'loading' | 'ready' | 'error' | 'added'>('idle');
  const [items, setItems] = useState<SiteRequestItem[]>([]);

  useEffect(() => {
    const incoming = new URLSearchParams(window.location.hash.slice(1)).get('repeat');
    if (incoming) {
      token.current = incoming;
      window.history.replaceState(window.history.state, '', `${window.location.pathname}${window.location.search}`);
    }
    if (!token.current) return;
    const controller = new AbortController();
    let active = true;
    setState('loading');
    void fetch('/api/v1/public/requests/repeat/resolve', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ token: token.current }),
      cache: 'no-store',
      credentials: 'same-origin',
      signal: controller.signal,
    }).then(async (response) => {
      if (!response.ok) throw new Error('repeat_unavailable');
      const data = await response.json() as { items: SiteRequestItem[] };
      if (!Array.isArray(data.items) || !data.items.length) throw new Error('repeat_empty');
      if (!active) return;
      setItems(data.items);
      setState('ready');
      track('request_open', { form_type: 'repeat', items: data.items.length });
    }).catch(() => {
      if (active) setState('error');
    });
    return () => { active = false; controller.abort(); };
  }, []);

  if (state === 'idle') return null;
  if (state === 'loading') return <p role="status" className="rounded-block bg-surface p-6 text-body text-text">{t('loading')}</p>;
  if (state === 'error') return <FormStatus kind="error" title={t('unavailable')}>{t('tryNew')}</FormStatus>;
  if (state === 'added') return <FormStatus kind="success" title={t('added')}>{t('reviewCart')}</FormStatus>;

  return (
    <section aria-labelledby="repeat-request-title" className="rounded-block border border-accent/40 bg-surface p-5 md:p-8">
      <h2 id="repeat-request-title" className="text-h3 font-medium text-text">{t('title')}</h2>
      <p className="mt-3 text-body text-text-secondary">{t('text')}</p>
      <ul className="my-5 grid gap-3">
        {items.map((item, index) => (
          <li key={index} className="rounded-field bg-surface-strong p-4 text-body text-text">
            <p className="chem-wrap font-medium">{item.name}</p>
            <p className="mt-1 text-small text-text-secondary">{[item.brand, item.catalogNumber, item.cas ? `CAS ${item.cas}` : '', item.packaging].filter(Boolean).join(' · ')}</p>
            <p className="mt-1 text-small text-text">{t('quantity', { count: item.quantity, unit: item.unit === 'pack' ? t('pack') : tu(item.unit) })}</p>
          </li>
        ))}
      </ul>
      <Button size="m" className="whitespace-normal" onClick={() => {
        for (const item of items) {
          useRfqStore.getState().addFree({ name: item.name, brand: item.brand, catalogNumber: item.catalogNumber, cas: item.cas,
            quantity: item.quantity, unit: item.unit, packagingLabel: item.packaging,
            requestedCustomPackaging: item.customPackaging, analogue: item.analogue });
        }
        token.current = null;
        setState('added');
      }}>{t('add')}</Button>
    </section>
  );
}
