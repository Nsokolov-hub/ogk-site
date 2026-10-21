import type { Metadata } from 'next';
import Image from 'next/image';
import { getTranslations, setRequestLocale } from 'next-intl/server';
import type { Locale } from '@/i18n/routing';
import type { BreadcrumbItem } from '@/types/content';
import { PageHeader } from '@/components/content/PageHeader';
import { RequestBlock } from '@/components/content/RequestBlock';
import { breadcrumbsLd, JsonLd } from '@/components/seo/JsonLd';
import { Container } from '@/components/ui/Container';
import { Link } from '@/i18n/navigation';
import { getSiteSettings } from '@/lib/api';
import { getBrands } from '@/lib/content-api';
import { pageMetadata, SITE_URL } from '@/lib/seo';

type Props = { params: Promise<{ locale: Locale }> };

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { locale } = await params;
  const t = await getTranslations({ locale, namespace: 'brands.list' });
  return pageMetadata({ locale, path: '/brands/', title: t('title'), description: t('description') });
}

/** Все производители (ТЗ 4.1): плитка бренда ведёт на его страницу */
export default async function BrandsPage({ params }: Props) {
  const { locale } = await params;
  setRequestLocale(locale);
  const t = await getTranslations('brands');
  const tc = await getTranslations('catalog');
  const [brands, settings] = await Promise.all([getBrands(locale), getSiteSettings()]);
  const breadcrumbs: BreadcrumbItem[] = [{ label: tc('home'), href: '/' }, { label: t('list.breadcrumb') }];
  const sorted = [...brands].sort((a, b) => a.wave - b.wave || b.count - a.count);

  return (
    <>
      <JsonLd data={breadcrumbsLd(breadcrumbs, SITE_URL, locale, '/brands/')} />
      <Container>
        <PageHeader breadcrumbs={breadcrumbs} title={t('list.h1')} lead={t('list.lead')} size="h1" />

        <ul className="mt-12 grid gap-3 sm:grid-cols-2 md:gap-4 lg:mt-16 lg:grid-cols-3 2xl:grid-cols-4">
          {sorted.map((b) => (
            <li key={b.slug}>
              <Link
                href={`/brands/${b.slug}/`}
                className="group flex h-full flex-col gap-5 rounded-block bg-surface p-5 transition-colors hover:bg-surface-strong md:p-6"
              >
                <span className="grid h-24 place-items-center rounded-field bg-base-deep px-6">
                  {b.logo ? (
                    <Image src={b.logo} alt="" width={212} height={172} unoptimized className="h-16 w-auto object-contain" />
                  ) : (
                    <span aria-hidden className="text-h3 font-medium text-text">
                      {b.name}
                    </span>
                  )}
                </span>
                <span className="flex flex-1 flex-col gap-2">
                  <span className="text-h4 font-medium text-text transition-colors group-hover:text-accent">{b.name}</span>
                  <span className="text-body text-text-secondary">{b.summary}</span>
                  <span className="mt-auto pt-2 text-small text-text">
                    {b.count ? t('list.count', { count: b.count }) : t('list.onRequest')}
                    {b.country ? <span className="text-text-secondary"> · {b.country}</span> : null}
                  </span>
                </span>
              </Link>
            </li>
          ))}
        </ul>

        <RequestBlock className="mt-20 lg:mt-28" title={t('list.requestTitle')} text={t('list.requestText')} docs={settings.docs} formType="brands_request" />
      </Container>
    </>
  );
}
