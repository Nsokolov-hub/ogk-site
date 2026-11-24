import type { Metadata } from 'next';
import { getTranslations, setRequestLocale } from 'next-intl/server';
import type { Locale } from '@/i18n/routing';
import { HeroPlates } from '@/components/home/HeroPlates';
import { SpecialOffers } from '@/components/home/SpecialOffers';
import { NotFoundBanner } from '@/components/home/NotFoundBanner';
import { ProductsSection } from '@/components/home/ProductsSection';
import { RequestSection } from '@/components/home/RequestSection';
import { SubscribeSection } from '@/components/home/SubscribeSection';
import { JsonLd, organizationLd, websiteLd } from '@/components/seo/JsonLd';
import { getHomeContent, getSiteSettings } from '@/lib/api';
import { previewParam } from '@/lib/content';
import { previewMetadata } from '@/lib/page-guard';
import { pageMetadata } from '@/lib/seo';

type Props = { params: Promise<{ locale: Locale }>; searchParams: Promise<{ preview?: string }> };

export async function generateMetadata({ params, searchParams }: Props): Promise<Metadata> {
  const { locale } = await params;
  const t = await getTranslations({ locale, namespace: 'home.meta' });
  const preview = previewParam((await searchParams).preview);
  return previewMetadata(pageMetadata({ locale, path: '/', title: t('title'), description: t('description'), hasEn: true }), !!preview);
}

export default async function HomePage({ params, searchParams }: Props) {
  const { locale } = await params;
  setRequestLocale(locale);
  const preview = previewParam((await searchParams).preview);
  const [content, settings] = await Promise.all([getHomeContent(locale, preview), getSiteSettings(locale)]);

  return (
    <div className="store-home">
      <JsonLd data={[organizationLd(settings), websiteLd(settings, locale)]} />
      <HeroPlates slides={content.hero.slides} />
      <SpecialOffers />
      <ProductsSection content={content.products} locale={locale} />
      <NotFoundBanner />
      <RequestSection request={content.request} docs={settings.docs} />
      <SubscribeSection subscribe={content.subscribe} docs={settings.docs} />
    </div>
  );
}
