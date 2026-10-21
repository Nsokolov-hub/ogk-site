import type { Metadata } from 'next';
import { ArrowRight } from 'lucide-react';
import { getTranslations, setRequestLocale } from 'next-intl/server';
import type { Locale } from '@/i18n/routing';
import type { BreadcrumbItem } from '@/types/content';
import { PageHeader } from '@/components/content/PageHeader';
import { RequestBlock } from '@/components/content/RequestBlock';
import { Requisites } from '@/components/content/Requisites';
import { breadcrumbsLd, JsonLd, organizationLd } from '@/components/seo/JsonLd';
import { Container } from '@/components/ui/Container';
import { Link } from '@/i18n/navigation';
import { getSiteSettings } from '@/lib/api';
import { aboutPage as page } from '@/data/mock/pages';
import { pageMetadata, SITE_URL } from '@/lib/seo';

type Props = { params: Promise<{ locale: Locale }> };

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { locale } = await params;
  return pageMetadata({ locale, path: '/about/', title: page.title, description: page.description, hasEn: page.hasEn });
}

/** О компании (ТЗ 10.4): чем занимаемся, как работаем, для кого, реквизиты */
export default async function AboutPage({ params }: Props) {
  const { locale } = await params;
  setRequestLocale(locale);
  const t = await getTranslations('trust');
  const tc = await getTranslations('catalog');
  const settings = await getSiteSettings();
  const breadcrumbs: BreadcrumbItem[] = [{ label: tc('home'), href: '/' }, { label: page.h1 }];
  const h2 = 'text-h3 font-medium text-text';

  return (
    <>
      <JsonLd data={[breadcrumbsLd(breadcrumbs, SITE_URL, locale, '/about/'), organizationLd(settings)]} />
      <Container>
        <PageHeader breadcrumbs={breadcrumbs} title={page.h1} lead={page.lead} size="h1" />

        {/* Подтверждённые цифры лендинга — крупно */}
        <dl className="mt-14 grid gap-8 sm:grid-cols-3 lg:mt-20">
          {page.facts.map((f) => (
            <div key={f.label} className="rounded-block bg-surface p-6 md:p-8">
              <dt className="sr-only">{f.label}</dt>
              <dd>
                <span className="block text-h1 font-medium text-accent">{f.value}</span>
                <span className="mt-2 block text-body text-text md:text-lg">{f.label}</span>
              </dd>
            </div>
          ))}
        </dl>

        <div className="mt-20 flex flex-col gap-20 lg:mt-28 lg:gap-28">
          <section aria-labelledby="about-directions">
            <h2 id="about-directions" className={h2}>
              {t('about.directions')}
            </h2>
            <ul className="mt-8 grid gap-3 md:grid-cols-2 md:gap-4">
              {page.directions.map((d) => (
                <li key={d.href}>
                  <Link href={d.href} className="group flex h-full flex-col gap-3 rounded-block bg-surface p-6 transition-colors hover:bg-surface-strong md:p-8">
                    <span className="flex items-center justify-between gap-4 text-h4 font-medium text-text transition-colors group-hover:text-accent">
                      {d.title}
                      <ArrowRight aria-hidden size={20} strokeWidth={1.5} className="shrink-0 text-accent transition-transform group-hover:translate-x-1" />
                    </span>
                    <span className="text-body text-text-secondary">{d.text}</span>
                  </Link>
                </li>
              ))}
            </ul>
          </section>

          <section aria-labelledby="about-steps">
            <h2 id="about-steps" className={h2}>
              {t('about.steps')}
            </h2>
            <ol className="mt-8 grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
              {page.steps.map((s, i) => (
                <li key={s.title} className="flex flex-col gap-3 rounded-block bg-surface p-6">
                  <span aria-hidden className="text-h2 font-medium leading-none text-accent">
                    {i + 1}
                  </span>
                  <h3 className="text-h4 font-medium text-text">{s.title}</h3>
                  <p className="text-body text-text-secondary">{s.text}</p>
                </li>
              ))}
            </ol>
          </section>

          <section aria-labelledby="about-audience" className="grid gap-10 lg:grid-cols-[minmax(0,4fr)_minmax(0,7fr)] lg:gap-16">
            <h2 id="about-audience" className={h2}>
              {t('about.audience')}
            </h2>
            <ul className="grid gap-x-10 gap-y-8 sm:grid-cols-2">
              {page.audience.map((a) => (
                <li key={a.title}>
                  <h3 className="text-h4 font-medium text-text">{a.title}</h3>
                  <p className="mt-2 text-body text-text-secondary">{a.text}</p>
                </li>
              ))}
            </ul>
          </section>

          <section aria-labelledby="about-requisites" className="grid gap-8 lg:grid-cols-[minmax(0,4fr)_minmax(0,7fr)] lg:gap-16">
            <div>
              <h2 id="about-requisites" className={h2}>
                {t('requisites.title')}
              </h2>
              <ul className="mt-6 flex flex-col gap-2 text-body">
                <li>
                  <Link href="/documents/" className="text-accent underline-offset-2 hover:underline">
                    {t('links.documents')}
                  </Link>
                </li>
                <li>
                  <Link href="/delivery/" className="text-accent underline-offset-2 hover:underline">
                    {t('links.delivery')}
                  </Link>
                </li>
                <li>
                  <Link href="/contacts/" className="text-accent underline-offset-2 hover:underline">
                    {t('links.contacts')}
                  </Link>
                </li>
              </ul>
            </div>
            <Requisites settings={settings} />
          </section>

          <RequestBlock title={t('requestTitle')} text={t('requestText')} docs={settings.docs} formType="about_request" />
        </div>
      </Container>
    </>
  );
}
