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
      className="fixed inset-x-3 bottom-3 z-[90] animate-sheet-up rounded-card bg-surface-raised p-4 shadow-[0_8px_24px_rgb(0_0_0/0.3)] md:inset-x-auto md:bottom-6 md:right-6 md:max-w-[480px] md:p-5" // taste-skill-ignore: плавающий баннер поверх страницы
    >
      <p className="text-small text-text">
        {t('text')}{' '}
        <a href={privacyHref} target="_blank" rel="noopener" className="text-accent underline-offset-2 hover:underline">
          {t('privacy')}
        </a>
      </p>
      <div className="mt-3 flex flex-wrap gap-2">
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
