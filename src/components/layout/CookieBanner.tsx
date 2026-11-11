'use client';

import { useEffect, useState } from 'react';
import { useTranslations } from 'next-intl';
import { Button } from '@/components/ui/Button';
import { getCookieConsent, setCookieConsent, type CookieConsent } from '@/lib/consent';

/**
 * Баннер согласия на аналитические cookies (NFR-06). Показывается, пока нет выбора.
 * Компактный (аудит 11.11.2026): на телефоне прежний занимал треть экрана и закрывал номер и CAS карточки, на
 * десктопе стоял над блоком заказа. Теперь мелкий текст и кнопки в одну строку, на десктопе — слева внизу.
 */
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
      className="fixed inset-x-3 bottom-3 z-[90] animate-sheet-up rounded-card glass-overlay p-3 shadow-[0_8px_24px_rgb(0_0_0/0.3)] md:inset-x-auto md:bottom-6 md:left-6 md:max-w-[420px] md:p-4" // taste-skill-ignore: плавающий баннер поверх страницы
    >
      <p className="text-caption text-text md:text-small">
        {t('text')}{' '}
        <a href={privacyHref} target="_blank" rel="noopener" className="text-accent underline-offset-2 hover:underline">
          {t('privacy')}
        </a>
      </p>
      <div className="mt-2.5 flex gap-2">
        <Button size="s" className="h-9 flex-auto px-3 md:h-10 md:flex-none md:px-5" onClick={() => choose('all')}>
          {t('acceptAll')}
        </Button>
        <Button size="s" variant="menu" className="h-9 flex-auto px-3 md:h-10 md:flex-none md:px-5" onClick={() => choose('necessary')}>
          {t('necessary')}
        </Button>
      </div>
    </section>
  );
}
