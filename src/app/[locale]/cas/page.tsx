import type { Metadata } from 'next';
import { getTranslations, setRequestLocale } from 'next-intl/server';
import type { Locale } from '@/i18n/routing';
import type { BreadcrumbItem } from '@/types/content';
import { CasLinks } from '@/components/content/CasLinks';
import { PageHeader } from '@/components/content/PageHeader';
import { breadcrumbsLd, JsonLd } from '@/components/seo/JsonLd';
import { Container } from '@/components/ui/Container';
import { Link } from '@/i18n/navigation';
import { getCasIndex } from '@/lib/product-api';
import { CAS_EN_INDEXED, pageMetadata, SITE_URL } from '@/lib/seo';

type Props = { params: Promise<{ locale: Locale }> };

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { locale } = await params;
  const t = await getTranslations({ locale, namespace: 'casIndex' });
  const index = await getCasIndex();
  return pageMetadata({ locale, path: '/cas/', title: t('meta.title'), description: t('meta.description', { count: index.total }), hasEn: CAS_EN_INDEXED });
}

/**
 * Указатель веществ по CAS (03.11.2026): буквы латинского алфавита и самые востребованные вещества.
 * Через него до каждой страницы /cas/<cas>/ два перехода с индексируемых страниц, а не только Sitemap.
 */
export default async function CasIndexPage({ params }: Props) {
  const { locale } = await params;
  setRequestLocale(locale);
  const t = await getTranslations('casIndex');
  const tc = await getTranslations('catalog');
  const index = await getCasIndex();
  const breadcrumbs: BreadcrumbItem[] = [{ label: tc('home'), href: '/' }, { label: t('breadcrumb') }];

  return (
    <>
      <JsonLd data={breadcrumbsLd(breadcrumbs, SITE_URL, locale, '/cas/')} />
      <Container>
        <PageHeader breadcrumbs={breadcrumbs} title={t('h1')} lead={t('lead', { count: index.total })} />

        <nav aria-label={t('letters')} className="mt-10">
          <ul className="flex flex-wrap gap-2">
            {index.letters.map((l) => (
              <li key={l.letter}>
                <Link
                  href={`/cas/letter/${l.letter}/`}
                  className="inline-flex h-11 min-w-11 items-center justify-center gap-2 rounded-full bg-surface-strong px-4 text-body font-medium text-text transition-colors hover:text-accent"
                >
                  {l.letter === '0' ? t('other') : l.letter.toUpperCase()}
                  <span className="text-small tabular-nums text-text-secondary">{l.count}</span>
                </Link>
              </li>
            ))}
          </ul>
        </nav>

        {index.popular.length ? (
          <section aria-labelledby="cas-popular" className="mt-16 lg:mt-20">
            <h2 id="cas-popular" className="text-h3 font-medium text-text">
              {t('popular')}
            </h2>
            <div className="mt-6">
              <CasLinks items={index.popular} locale={locale} offersLabel={(count) => t('offers', { count })} />
            </div>
          </section>
        ) : null}

        <p className="mt-16 max-w-[72ch] text-body text-text-secondary">
          {t('hint')}{' '}
          <Link href="/substances/" className="font-medium text-accent hover:text-accent-hover">
            {t('substances')}
          </Link>
        </p>
      </Container>
    </>
  );
}
