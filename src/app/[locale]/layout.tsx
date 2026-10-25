import type { Metadata, Viewport } from 'next';
import { Suspense, type ReactNode } from 'react';
import { Manrope } from 'next/font/google';
import { headers } from 'next/headers';
import { notFound } from 'next/navigation';
import { hasLocale, NextIntlClientProvider } from 'next-intl';
import { setRequestLocale } from 'next-intl/server';
import { routing } from '@/i18n/routing';
import { Counters } from '@/components/analytics/Counters';
import { CaptchaHost } from '@/components/forms/CaptchaHost';
import { CookieBanner } from '@/components/layout/CookieBanner';
import { Footer } from '@/components/layout/Footer';
import { Header } from '@/components/layout/Header';
import { Providers } from '@/components/layout/Providers';
import { SkipLink } from '@/components/layout/SkipLink';
import { OneClickOrderDialog } from '@/components/product/OneClickOrderDialog';
import { getCatalogTree, getSiteSettings } from '@/lib/api';
import '../globals.css';

// Временный шрифт до подключения LT Superior (ТЗ 11.1)
const manrope = Manrope({
  subsets: ['latin', 'cyrillic'],
  weight: ['400', '500', '600', '700'],
  variable: '--font-manrope',
  display: 'swap',
});

export const metadata: Metadata = {
  metadataBase: new URL('https://www.ogk-chem.ru'),
  icons: { icon: '/images/brand/favicon.svg' },
};

export const viewport: Viewport = {
  themeColor: '#1c1c1c',
  colorScheme: 'dark',
};

// Страницы собираются на запрос: данные каталога приходят из API и кэшируются на уровне запросов (Data Cache)
// с тегами — правка товара сбрасывает кэш его страницы. Так сборка витрины не зависит от доступности API.
export const dynamic = 'force-dynamic';

export function generateStaticParams() {
  return routing.locales.map((locale) => ({ locale }));
}

export default async function LocaleLayout({ children, params }: { children: ReactNode; params: Promise<{ locale: string }> }) {
  const { locale } = await params;
  if (!hasLocale(routing.locales, locale)) notFound();
  setRequestLocale(locale);

  const [settings, tree, requestHeaders] = await Promise.all([getSiteSettings(locale), getCatalogTree(locale), headers()]);
  // Номера счётчиков — из окружения при запросе: у стейджа и продакшена свои (ТЗ 15.1)
  const ymId = Number.parseInt(process.env.YM_COUNTER_ID ?? '', 10);
  const counterIds = { ym: Number.isFinite(ymId) ? ymId : null, ga: process.env.GA_MEASUREMENT_ID || null };

  return (
    <html lang={locale} className={manrope.variable}>
      <body>
        <NextIntlClientProvider>
          <Providers />
          <SkipLink />
          <Header settings={settings} tree={tree} />
          <main id="main" tabIndex={-1} className="outline-none">
            {children}
          </main>
          <Footer settings={settings} />
          <OneClickOrderDialog docs={settings.docs} />
          <CaptchaHost />
          <CookieBanner privacyHref={settings.docs.privacy} />
          <Suspense fallback={null}>
            <Counters ids={counterIds} nonce={requestHeaders.get('x-nonce') ?? undefined} />
          </Suspense>
        </NextIntlClientProvider>
      </body>
    </html>
  );
}
