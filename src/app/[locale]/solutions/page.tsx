import type { Metadata } from 'next';
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
import { getSolutions } from '@/lib/content-api';
import { pageMetadata, SITE_URL } from '@/lib/seo';

type Props = { params: Promise<{ locale: Locale }> };

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { locale } = await params;
  const t = await getTranslations({ locale, namespace: 'solutions.list' });
  return pageMetadata({ locale, path: '/solutions/', title: t('title'), description: t('description') });
}

/** Отраслевые решения (ТЗ 4.1): список посадочных под типы лабораторий */
export default async function SolutionsPage({ params }: Props) {
  const { locale } = await params;
  setRequestLocale(locale);
  const t = await getTranslations('solutions');
  const tc = await getTranslations('catalog');
  const [list, settings] = await Promise.all([getSolutions(locale), getSiteSettings(locale)]);
  const breadcrumbs: BreadcrumbItem[] = [{ label: tc('home'), href: '/' }, { label: t('list.breadcrumb') }];

  return (
    <>
      <JsonLd data={breadcrumbsLd(breadcrumbs, SITE_URL, locale, '/solutions/')} />
      <Container>
        <PageHeader breadcrumbs={breadcrumbs} title={t('list.h1')} lead={t('list.lead')} size="h1" />

        <ul className="mt-12 grid gap-4 md:grid-cols-2 lg:mt-16">
          {list.map((s) => (
            <li key={s.slug}>
              <Link
                href={`/solutions/${s.slug}/`}
                className="group flex h-full flex-col gap-6 rounded-block bg-surface p-6 transition-colors hover:bg-surface-strong md:p-10"
              >
                <div>
                  <h2 className="text-h3 font-medium text-text transition-colors group-hover:text-accent">{s.h1}</h2>
                  <p className="mt-3 text-body text-text-secondary md:text-lg">{s.summary}</p>
                </div>
                <ul className="flex flex-col gap-2">
                  {s.tasks.slice(0, 3).map((task) => (
                    <li key={task} className="flex gap-3 text-body text-text">
                      <span aria-hidden className="mt-2.5 size-1.5 shrink-0 rounded-full bg-accent" />
                      {task}
                    </li>
                  ))}
                </ul>
                <span className="mt-auto inline-flex items-center gap-2 text-body font-semibold text-accent sm:text-lg">
                  {t('list.more')}
                  <ArrowRight aria-hidden size={20} strokeWidth={1.5} className="transition-transform group-hover:translate-x-1" />
                </span>
              </Link>
            </li>
          ))}
        </ul>

        <RequestBlock className="mt-20 lg:mt-28" title={t('list.requestTitle')} text={t('list.requestText')} docs={settings.docs} formType="solutions_request" />
      </Container>
    </>
  );
}
