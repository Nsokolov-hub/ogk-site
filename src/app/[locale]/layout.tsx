import type { Metadata, Viewport } from 'next';
import { Suspense, type ReactNode } from 'react';
import { Manrope } from 'next/font/google';
import { headers } from 'next/headers';
import { notFound } from 'next/navigation';
import { hasLocale, NextIntlClientProvider } from 'next-intl';
import { getMessages, setRequestLocale } from 'next-intl/server';
import { clientMessages } from '@/i18n/client-messages';
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
import { getSite } from '@/lib/content';
import { siteMenu } from '@/lib/site-menu';
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
  // favicon.ico — для поиска Яндекса и старых браузеров, которые берут значок только по этому адресу; SVG — для
  // остальных; apple-touch-icon и манифест — для закладок и экрана телефона (аудит 12.11.2026: отдавали 404)
  icons: {
    icon: [
      { url: '/favicon.ico', sizes: '48x48' },
      { url: '/images/brand/favicon.svg', type: 'image/svg+xml' },
    ],
    apple: '/apple-touch-icon.png',
  },
  manifest: '/manifest.webmanifest',
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

  const [settings, tree, requestHeaders, site, messages] = await Promise.all([
    getSiteSettings(locale),
    getCatalogTree(locale),
    headers(),
    getSite(),
    getMessages(),
  ]);
  const menu = await siteMenu(locale, tree);
  // Номера счётчиков (ТЗ 15.1): из настроек админки, иначе из окружения сервера — у стейджа и продакшена свои
  const ymId = Number.parseInt(process.env.YM_COUNTER_ID ?? '', 10);
  const counterIds = {
    ym: site.counters.ym ?? (Number.isFinite(ymId) ? ymId : null),
    ga: site.counters.ga ?? (process.env.GA_MEASUREMENT_ID || null),
  };

  return (
    <html lang={locale} className={manrope.variable}>
      <body>
        {/* В браузер — только разделы словаря, которые читают клиентские компоненты (i18n/client-messages) */}
        <NextIntlClientProvider messages={clientMessages(messages)}>
          <Providers />
          <SkipLink />
          <Header settings={settings} menu={menu} />
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
