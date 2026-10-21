'use client';

import { useLocale, useTranslations } from 'next-intl';
import { usePathname } from '@/i18n/navigation';
import { routing, type Locale } from '@/i18n/routing';
import { cn } from '@/lib/cn';

/** Адрес той же страницы в другой локали: RU без префикса, EN — /en/… (сразу канонический, без редиректа) */
function localizedPath(pathname: string, locale: Locale) {
  const path = pathname.endsWith('/') ? pathname : `${pathname}/`;
  return locale === routing.defaultLocale ? path : `/${locale}${path === '/' ? '/' : path}`;
}

/** RU / EN — ведёт на ту же страницу в другой локали (EN-03) */
export function LangSwitcher({ className }: { className?: string }) {
  const t = useTranslations('header');
  const locale = useLocale();
  const pathname = usePathname();

  return (
    <nav aria-label={t('langLabel')} className={cn('flex shrink-0 items-center rounded-pill border border-border p-0.5', className)}>
      {routing.locales.map((l) => {
        const active = l === locale;
        return (
          <a
            key={l}
            href={localizedPath(pathname, l)}
            hrefLang={l}
            lang={l}
            aria-current={active ? 'true' : undefined}
            className={cn(
              'inline-grid h-8 min-w-9 place-items-center rounded-pill px-2 text-small font-medium uppercase transition-colors',
              active ? 'bg-accent text-text-on-accent' : 'text-text-secondary hover:text-text',
            )}
          >
            {l}
          </a>
        );
      })}
    </nav>
  );
}
