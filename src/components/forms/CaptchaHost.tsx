'use client';

import { useEffect, useRef } from 'react';
import { useTranslations } from 'next-intl';
import { Dialog } from '@/components/ui/Dialog';
import { cancelCaptcha, captchaSiteKey, solveCaptcha, useCaptchaStore } from '@/lib/captcha-store';

const SCRIPT_URL = 'https://smartcaptcha.yandexcloud.net/captcha.js';

declare global {
  interface Window {
    smartCaptcha?: {
      render: (container: HTMLElement, params: { sitekey: string; hl: string; callback: (token: string) => void }) => number;
      destroy: (widgetId?: number) => void;
    };
  }
}

let loading: Promise<void> | null = null;

function loadScript(): Promise<void> {
  if (window.smartCaptcha) return Promise.resolve();
  loading ??= new Promise((resolve, reject) => {
    const script = document.createElement('script');
    script.src = SCRIPT_URL;
    script.async = true;
    script.onload = () => resolve();
    script.onerror = () => {
      loading = null;
      reject(new Error('captcha script'));
    };
    document.head.appendChild(script);
  });
  return loading;
}

/** Окно SmartCaptcha; скрипт капчи грузится только когда окно открылось */
export function CaptchaHost() {
  const t = useTranslations('captcha');
  const { open, lang } = useCaptchaStore();
  const container = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    let widget: number | undefined;
    let cancelled = false;
    loadScript()
      .then(() => {
        if (cancelled || !container.current || !window.smartCaptcha) return;
        widget = window.smartCaptcha.render(container.current, { sitekey: captchaSiteKey(), hl: lang, callback: solveCaptcha });
      })
      .catch(() => cancelCaptcha());
    return () => {
      cancelled = true;
      if (widget !== undefined) window.smartCaptcha?.destroy(widget);
    };
  }, [open, lang]);

  return (
    <Dialog open={open} onOpenChange={(next) => (next ? undefined : cancelCaptcha())} title={t('title')} description={t('text')} closeLabel={t('close')}>
      <div ref={container} className="min-h-[102px]" />
    </Dialog>
  );
}
