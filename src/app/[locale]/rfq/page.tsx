import type { Metadata } from 'next';
import { getTranslations, setRequestLocale } from 'next-intl/server';
import type { Locale } from '@/i18n/routing';
import type { BreadcrumbItem } from '@/types/content';
import { PageHeader } from '@/components/content/PageHeader';
import { RfqPage } from '@/components/rfq/RfqPage';
import { Container } from '@/components/ui/Container';
import { getSiteSettings } from '@/lib/api';
import { serviceMetadata } from '@/lib/seo';

type Props = { params: Promise<{ locale: Locale }> };

/** Корзина запроса — служебная страница: noindex и Disallow в robots.txt (ТЗ 4.1, SEO-03) */
export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { locale } = await params;
  const t = await getTranslations({ locale, namespace: 'rfq' });
  return serviceMetadata(t('metaTitle'));
}

export default async function RfqRoute({ params }: Props) {
  const { locale } = await params;
  setRequestLocale(locale);
  const t = await getTranslations('rfq');
  const tc = await getTranslations('catalog');
  const settings = await getSiteSettings();
  const breadcrumbs: BreadcrumbItem[] = [{ label: tc('home'), href: '/' }, { label: t('h1') }];

  return (
    <Container>
      <PageHeader breadcrumbs={breadcrumbs} title={t('h1')} lead={t('lead')} />
      <RfqPage docs={settings.docs} />
    </Container>
  );
}
