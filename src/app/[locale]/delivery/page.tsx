import type { Metadata } from 'next';
import { CircleCheck } from 'lucide-react';
import { getTranslations, setRequestLocale } from 'next-intl/server';
import type { Locale } from '@/i18n/routing';
import type { BreadcrumbItem } from '@/types/content';
import { FaqSection } from '@/components/content/FaqSection';
import { LinkChips } from '@/components/content/LinkChips';
import { PageHeader } from '@/components/content/PageHeader';
import { RequestBlock } from '@/components/content/RequestBlock';
import { breadcrumbsLd, faqLd, JsonLd } from '@/components/seo/JsonLd';
import { Chip } from '@/components/ui/Chip';
import { Container } from '@/components/ui/Container';
import { getSiteSettings } from '@/lib/api';
import { deliveryPage as page } from '@/data/mock/pages';
import { COUNTRIES } from '@/data/mock/services';
import { pageMetadata, SITE_URL } from '@/lib/seo';

type Props = { params: Promise<{ locale: Locale }> };

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { locale } = await params;
  return pageMetadata({ locale, path: '/delivery/', title: page.title, description: page.description, hasEn: page.hasEn });
}

/** Доставка и условия поставки (ТЗ 10.4): география, сроки, температура, оплата, документы */
export default async function DeliveryPage({ params }: Props) {
  const { locale } = await params;
  setRequestLocale(locale);
  const t = await getTranslations('trust');
  const tc = await getTranslations('catalog');
  const settings = await getSiteSettings();
  const breadcrumbs: BreadcrumbItem[] = [{ label: tc('home'), href: '/' }, { label: page.h1 }];

  return (
    <>
      <JsonLd data={[breadcrumbsLd(breadcrumbs, SITE_URL, locale, '/delivery/'), faqLd(page.faq)]} />
      <Container>
        <PageHeader breadcrumbs={breadcrumbs} title={page.h1} lead={page.lead} size="h1" />

        {/* Оглавление-якоря: разделы длинной страницы условий */}
        <nav aria-label={t('delivery.toc')} className="mt-10">
          <ul className="flex flex-wrap gap-2">
            {page.sections.map((s) => (
              <li key={s.id}>
                <a href={`#${s.id}`} className="inline-flex h-10 items-center rounded-pill bg-surface-strong px-4 text-small text-text transition-colors hover:text-accent md:text-body">
                  {s.title}
                </a>
              </li>
            ))}
          </ul>
        </nav>

        <div className="mt-16 flex flex-col gap-4 lg:mt-20">
          {page.sections.map((s) => (
            <section
              key={s.id}
              id={s.id}
              aria-labelledby={`${s.id}-title`}
              className="grid scroll-mt-32 gap-6 rounded-block bg-surface p-6 md:p-10 lg:grid-cols-[minmax(0,4fr)_minmax(0,7fr)] lg:gap-16"
            >
              <h2 id={`${s.id}-title`} className="text-h3 font-medium text-text">
                {s.title}
              </h2>
              <div className="flex flex-col gap-5">
                {s.text ? <p className="text-body text-text md:text-lg">{s.text}</p> : null}
                {s.items ? (
                  <ul className="flex flex-col gap-3">
                    {s.items.map((item) => (
                      <li key={item} className="flex gap-3 text-body text-text md:text-lg">
                        <CircleCheck aria-hidden size={22} strokeWidth={1.5} className="mt-0.5 shrink-0 text-accent" />
                        {item}
                      </li>
                    ))}
                  </ul>
                ) : null}
                {s.id === 'geo' ? (
                  <ul className="flex flex-wrap gap-2" aria-label={t('delivery.countries')}>
                    {COUNTRIES.map((c) => (
                      <li key={c}>
                        <Chip label={c} />
                      </li>
                    ))}
                  </ul>
                ) : null}
              </div>
            </section>
          ))}
        </div>

        <div className="mt-20 flex flex-col gap-20 lg:mt-28 lg:gap-28">
          <FaqSection id="delivery-faq" title={t('faq')} items={page.faq} />
          <LinkChips id="delivery-links" title={t('related')} items={page.links} />
          <RequestBlock title={t('requestTitle')} text={t('requestText')} docs={settings.docs} formType="delivery_request" />
        </div>
      </Container>
    </>
  );
}
