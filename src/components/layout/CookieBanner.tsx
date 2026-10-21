'use client';

import { useEffect, useState } from 'react';
import { useTranslations } from 'next-intl';
import { Button } from '@/components/ui/Button';
import { getCookieConsent, setCookieConsent, type CookieConsent } from '@/lib/consent';

/** Баннер согласия на аналитические cookies (NFR-06). Показывается, пока нет выбора. */
export function CookieBanner({ privacyHref }: { privacyHref: string }) {
  const t = useTranslations('cookie');
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    setVisible(getCookieConsent() === null);
  }, []);

  if (!visible) return null;

  const choose = (value: CookieConsent) => {
    setCookieConsent(value);
    setVisible(false);
  };

  return (
    <section
      aria-label={t('label')}
      className="fixed inset-x-3 bottom-3 z-[90] mx-auto max-w-[760px] animate-sheet-up rounded-card border border-border bg-surface-raised p-5 shadow-[0_24px_80px_rgb(0_0_0/0.5)] md:bottom-6 md:rounded-block md:p-6"
    >
      <p className="text-small text-text md:text-body">
        {t('text')}{' '}
        <a href={privacyHref} target="_blank" rel="noopener" className="text-accent underline-offset-2 hover:underline">
          {t('privacy')}
        </a>
      </p>
      <div className="mt-4 flex flex-wrap gap-3">
        <Button size="s" onClick={() => choose('all')}>
          {t('acceptAll')}
        </Button>
        <Button size="s" variant="menu" onClick={() => choose('necessary')}>
          {t('necessary')}
        </Button>
      </div>
    </section>
  );
}
