import type { Metadata } from 'next';
import { getTranslations, setRequestLocale } from 'next-intl/server';
import type { Locale } from '@/i18n/routing';
import { BrandsSection } from '@/components/home/BrandsSection';
import { CapabilitiesSection } from '@/components/home/CapabilitiesSection';
import { HeroSearch } from '@/components/home/HeroSearch';
import { HeroSlider } from '@/components/home/HeroSlider';
import { ProductsSection } from '@/components/home/ProductsSection';
import { QualitySection } from '@/components/home/QualitySection';
import { RequestSection } from '@/components/home/RequestSection';
import { ServicesSection } from '@/components/home/ServicesSection';
import { SubscribeSection } from '@/components/home/SubscribeSection';
import { WhyUsSection } from '@/components/home/WhyUsSection';
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
    <>
      <JsonLd data={[organizationLd(settings), websiteLd(settings, locale)]} />
      <HeroSlider slides={content.hero.slides} />
      <HeroSearch search={content.hero.search} facts={content.hero.facts} />
      <ProductsSection content={content.products} locale={locale} />
      <BrandsSection brands={content.brands} promo={content.promo} />
      <QualitySection quality={content.quality} />
      <ServicesSection services={content.services} />
      <WhyUsSection whyUs={content.whyUs} />
      <CapabilitiesSection capabilities={content.capabilities} />
      <RequestSection request={content.request} docs={settings.docs} />
      <SubscribeSection subscribe={content.subscribe} docs={settings.docs} />
    </>
  );
}
