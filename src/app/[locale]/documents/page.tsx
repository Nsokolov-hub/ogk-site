import type { Metadata } from 'next';
import { FileText } from 'lucide-react';
import { getTranslations, setRequestLocale } from 'next-intl/server';
import type { Locale } from '@/i18n/routing';
import type { BreadcrumbItem } from '@/types/content';
import { PageHeader } from '@/components/content/PageHeader';
import { RequestBlock } from '@/components/content/RequestBlock';
import { RequestDocButton } from '@/components/content/RequestDocButton';
import { Requisites } from '@/components/content/Requisites';
import { breadcrumbsLd, JsonLd } from '@/components/seo/JsonLd';
import { Container } from '@/components/ui/Container';
import { getSiteSettings } from '@/lib/api';
import { documentsPageEn } from '@/data/mock/en/pages';
import { documentsPage } from '@/data/mock/pages';
import { pageMetadata, SITE_URL } from '@/lib/seo';

type Props = { params: Promise<{ locale: Locale }> };

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { locale } = await params;
  const page = locale === 'en' ? documentsPageEn : documentsPage;
  return pageMetadata({ locale, path: '/documents/', title: page.title, description: page.description, hasEn: page.hasEn });
}

/** Документы (ТЗ 10.4): реквизиты, юридические документы (те же адреса /files/*.pdf), ЭДО, сопроводительные документы */
export default async function DocumentsPage({ params }: Props) {
  const { locale } = await params;
  const page = locale === 'en' ? documentsPageEn : documentsPage;
  setRequestLocale(locale);
  const t = await getTranslations('trust');
  const tc = await getTranslations('catalog');
  const settings = await getSiteSettings(locale);
  const breadcrumbs: BreadcrumbItem[] = [{ label: tc('home'), href: '/' }, { label: page.h1 }];
  const h2 = 'text-h3 font-medium text-text';
  const legal = [
    { title: t('documents.card'), href: settings.docs.card },
    { title: t('documents.privacy'), href: settings.docs.privacy },
    { title: t('documents.consent'), href: settings.docs.consent },
  ];

  return (
    <>
      <JsonLd data={breadcrumbsLd(breadcrumbs, SITE_URL, locale, '/documents/')} />
      <Container>
        <PageHeader breadcrumbs={breadcrumbs} title={page.h1} lead={page.lead} size="h1" />

        <div className="mt-16 flex flex-col gap-20 lg:mt-20 lg:gap-28">
          <section aria-labelledby="docs-legal" className="grid gap-8 lg:grid-cols-[minmax(0,4fr)_minmax(0,7fr)] lg:gap-16">
            <h2 id="docs-legal" className={h2}>
              {t('documents.legal')}
            </h2>
            <ul className="flex flex-col gap-3">
              {legal.map((d) => (
                <li key={d.href}>
                  <a
                    href={d.href}
                    target="_blank"
                    rel="noopener"
                    className="flex items-center gap-4 rounded-field bg-surface px-5 py-4 text-body text-text transition-colors hover:bg-surface-strong hover:text-accent md:text-lg"
                  >
                    <FileText aria-hidden size={24} strokeWidth={1.5} className="shrink-0 text-accent" />
                    <span className="flex-1">{d.title}</span>
                    <span className="text-small text-text-secondary">PDF</span>
                    <span className="sr-only"> {t('newTab')}</span>
                  </a>
                </li>
              ))}
            </ul>
          </section>

          <section aria-labelledby="docs-requisites" className="grid gap-8 lg:grid-cols-[minmax(0,4fr)_minmax(0,7fr)] lg:gap-16">
            <div>
              <h2 id="docs-requisites" className={h2}>
                {t('requisites.title')}
              </h2>
              <p className="mt-4 text-body text-text-secondary md:text-lg">{page.edo}</p>
            </div>
            <Requisites settings={settings} />
          </section>

          <section aria-labelledby="docs-supply">
            <h2 id="docs-supply" className={h2}>
              {t('documents.supply')}
            </h2>
            <ul className="mt-8 grid gap-3 md:grid-cols-2 md:gap-4">
              {page.supplyDocs.map((d) => (
                <li key={d.title} className="flex flex-col gap-4 rounded-block bg-surface p-6 md:p-8">
                  <h3 className="text-h4 font-medium text-text">{d.title}</h3>
                  <p className="flex-1 text-body text-text-secondary">{d.text}</p>
                  <RequestDocButton
                    label={t('documents.requestSample')}
                    text={t('documents.requestSampleText', { doc: d.title })}
                    className="self-start"
                  />
                </li>
              ))}
            </ul>
            <p className="mt-6 max-w-[72ch] text-body text-text-secondary">{page.licenses}</p>
          </section>

          <RequestBlock title={t('documents.requestTitle')} text={t('documents.requestText')} docs={settings.docs} formType="documents_request" />
        </div>
      </Container>
    </>
  );
}
