import type { Metadata } from 'next';
import Image from 'next/image';
import { ArrowRight } from 'lucide-react';
import { getTranslations, setRequestLocale } from 'next-intl/server';
import type { Locale } from '@/i18n/routing';
import type { BreadcrumbItem } from '@/types/content';
import { PageHeader } from '@/components/content/PageHeader';
import { RequestBlock } from '@/components/content/RequestBlock';
import { breadcrumbsLd, JsonLd } from '@/components/seo/JsonLd';
import { Container } from '@/components/ui/Container';
import { Link } from '@/i18n/navigation';
import { getSiteSettings } from '@/lib/api';
import { getServices } from '@/lib/content-api';
import { pageMetadata, SITE_URL } from '@/lib/seo';

type Props = { params: Promise<{ locale: Locale }> };

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { locale } = await params;
  const t = await getTranslations({ locale, namespace: 'services.list' });
  return pageMetadata({ locale, path: '/services/', title: t('title'), description: t('description') });
}

/** Список услуг (ТЗ 4.1): каждая строка — ссылка на страницу услуги с формой расчёта */
export default async function ServicesPage({ params }: Props) {
  const { locale } = await params;
  setRequestLocale(locale);
  const t = await getTranslations('services');
  const tc = await getTranslations('catalog');
  const [list, settings] = await Promise.all([getServices(locale), getSiteSettings()]);
  const breadcrumbs: BreadcrumbItem[] = [{ label: tc('home'), href: '/' }, { label: t('list.breadcrumb') }];
  const [featured, ...rest] = [list.find((s) => s.slug === 'cold-chain')!, ...list.filter((s) => s.slug !== 'cold-chain')];

  return (
    <>
      <JsonLd data={breadcrumbsLd(breadcrumbs, SITE_URL, locale, '/services/')} />
      <Container>
        <PageHeader breadcrumbs={breadcrumbs} title={t('list.h1')} lead={t('list.lead')} size="h1" />

        {/* Главная услуга лендинга — крупно, с изображением; остальные — списком */}
        <Link
          href={`/services/${featured.slug}/`}
          className="group mt-12 grid overflow-hidden rounded-block bg-surface transition-colors hover:bg-surface-strong lg:mt-16 lg:grid-cols-[minmax(0,6fr)_minmax(0,5fr)]"
        >
          <div className="flex flex-col justify-between gap-8 p-6 md:p-10 lg:p-14">
            <div>
              <h2 className="text-h2 font-medium text-text transition-colors group-hover:text-accent">{featured.h1}</h2>
              <p className="mt-4 max-w-[52ch] text-lead text-text">{featured.summary}</p>
            </div>
            <span className="inline-flex items-center gap-2 text-body font-semibold text-accent sm:text-lg">
              {t('list.more')}
              <ArrowRight aria-hidden size={20} strokeWidth={1.5} className="transition-transform group-hover:translate-x-1" />
            </span>
          </div>
          {featured.image ? (
            <div className="relative min-h-[220px] bg-base-deep lg:min-h-[360px]">
              <Image src={featured.image.src} alt={featured.image.alt} fill sizes="(min-width: 1024px) 45vw, 100vw" className="object-contain p-6 lg:p-10" />
            </div>
          ) : null}
        </Link>

        <ul className="mt-4 flex flex-col gap-2 md:mt-6">
          {rest.map((s) => (
            <li key={s.slug}>
              <Link
                href={`/services/${s.slug}/`}
                className="group grid gap-2 rounded-block px-6 py-6 transition-colors hover:bg-surface md:grid-cols-[minmax(0,5fr)_minmax(0,6fr)_auto] md:items-center md:gap-10 md:px-10 md:py-8"
              >
                <h2 className="text-h3 font-medium text-text transition-colors group-hover:text-accent">{s.h1}</h2>
                <p className="text-body text-text-secondary md:text-lg">{s.summary}</p>
                <ArrowRight aria-hidden size={24} strokeWidth={1.5} className="hidden text-accent transition-transform group-hover:translate-x-1 md:block" />
              </Link>
            </li>
          ))}
        </ul>

        <RequestBlock className="mt-20 lg:mt-28" title={t('list.requestTitle')} text={t('list.requestText')} docs={settings.docs} formType="services_request" />
      </Container>
    </>
  );
}
