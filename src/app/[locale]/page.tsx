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
import { pageMetadata } from '@/lib/seo';

type Props = { params: Promise<{ locale: Locale }> };

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { locale } = await params;
  const t = await getTranslations({ locale, namespace: 'home.meta' });
  // EN-контент главной ещё не переведён: /en/ — noindex с canonical на русскую версию (EN-05)
  return pageMetadata({ locale, path: '/', title: t('title'), description: t('description'), hasEn: true });
}

export default async function HomePage({ params }: Props) {
  const { locale } = await params;
  setRequestLocale(locale);
  const [content, settings] = await Promise.all([getHomeContent(locale), getSiteSettings(locale)]);

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
