import type { Metadata } from 'next';
import { getTranslations, setRequestLocale } from 'next-intl/server';
import type { Locale } from '@/i18n/routing';
import type { BreadcrumbItem } from '@/types/content';
import { PageHeader } from '@/components/content/PageHeader';
import { UnsubscribeForm } from '@/components/subscribe/UnsubscribeForm';
import { Container } from '@/components/ui/Container';
import { serviceMetadata } from '@/lib/seo';

type Props = { params: Promise<{ locale: Locale }>; searchParams: Promise<{ t?: string }> };

/** Отписка по ссылке из письма (NFR-07): служебная страница, noindex. Отписывает кнопка, а не сам переход —
 *  почтовые сканеры открывают ссылки из писем и не должны отписывать людей */
export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { locale } = await params;
  const t = await getTranslations({ locale, namespace: 'unsubscribe' });
  return serviceMetadata(t('metaTitle'));
}

export default async function UnsubscribeRoute({ params, searchParams }: Props) {
  const { locale } = await params;
  const { t: token } = await searchParams;
  setRequestLocale(locale);
  const t = await getTranslations('unsubscribe');
  const tc = await getTranslations('catalog');
  const breadcrumbs: BreadcrumbItem[] = [{ label: tc('home'), href: '/' }, { label: t('h1') }];
  return (
    <Container>
      <PageHeader breadcrumbs={breadcrumbs} title={t('h1')} lead={t('lead')} />
      <div className="pb-20">
        <UnsubscribeForm token={typeof token === 'string' ? token : ''} />
      </div>
    </Container>
  );
}
