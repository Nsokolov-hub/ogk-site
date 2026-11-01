import type { Metadata } from 'next';
import { notFound } from 'next/navigation';
import { getTranslations, setRequestLocale } from 'next-intl/server';
import type { Locale } from '@/i18n/routing';
import type { BreadcrumbItem } from '@/types/content';
import { Formula } from '@/components/content/Formula';
import { PageHeader } from '@/components/content/PageHeader';
import { RequestBlock } from '@/components/content/RequestBlock';
import { SubstancePicker } from '@/components/product/SubstancePicker';
import { breadcrumbsLd, JsonLd } from '@/components/seo/JsonLd';
import { Container } from '@/components/ui/Container';
import { Link, permanentRedirect } from '@/i18n/navigation';
import { getSiteSettings } from '@/lib/api';
import { getCasPage } from '@/lib/product-api';
import { pageMetadata, SITE_URL } from '@/lib/seo';

type Props = { params: Promise<{ locale: Locale; cas: string }> };

const BRANDS_IN_TEXT = 5;
const BRANDS_IN_FACTS = 8;

/**
 * Вещество по CAS: все предложения каталога с этим CAS от разных производителей на одной странице.
 * Страницы собирает бэкенд каждую ночь (app.catalog.cas_pages) — для CAS, который продают хотя бы два бренда.
 */
export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { locale, cas } = await params;
  const t = await getTranslations({ locale, namespace: 'casPage' });
  const data = await getCasPage(cas, locale, t('other'));
  if (!data || 'substance' in data) return {};
  const { page } = data;
  const brands = page.brands.slice(0, 4).join(', ');
  return pageMetadata({
    locale,
    path: `/cas/${page.cas}/`,
    title: t('meta.title', { name: page.name, cas: page.cas, count: page.offers }),
    description: t('meta.description', { name: page.name, cas: page.cas, count: page.offers, brands }),
    hasEn: true,
  });
}

export default async function CasPage({ params }: Props) {
  const { locale, cas } = await params;
  setRequestLocale(locale);
  const t = await getTranslations('casPage');
  const tc = await getTranslations('catalog');
  const [data, settings] = await Promise.all([getCasPage(cas, locale, t('other')), getSiteSettings(locale)]);
  if (!data) notFound();
  if ('substance' in data) return permanentRedirect({ href: `/substances/${data.substance}/`, locale });
  const { page, items, groups } = data;
  const path = `/cas/${page.cas}/`;

  const breadcrumbs: BreadcrumbItem[] = [
    { label: tc('home'), href: '/' },
    { label: t('breadcrumb'), href: '/catalog/' },
    { label: page.name },
  ];
  const textBrands = page.brands.slice(0, BRANDS_IN_TEXT).join(', ') + (page.brands.length > BRANDS_IN_TEXT ? ' …' : '');
  const factBrands =
    page.brands.slice(0, BRANDS_IN_FACTS).join(', ') +
    (page.brands.length > BRANDS_IN_FACTS ? ` ${t('facts.more', { count: page.brands.length - BRANDS_IN_FACTS })}` : '');

  const facts = [
    { label: t('facts.name'), value: page.name },
    { label: 'CAS', value: page.cas },
    ...(page.formula ? [{ label: t('facts.formula'), value: <Formula value={page.formula} /> }] : []),
    ...(page.molecularWeight ? [{ label: t('facts.mw'), value: t('facts.mwValue', { value: page.molecularWeight }) }] : []),
    { label: t('facts.items'), value: String(page.offers) },
    { label: t('facts.brands'), value: factBrands },
  ];

  return (
    <>
      <JsonLd data={breadcrumbsLd(breadcrumbs, SITE_URL, locale, path)} />
      <Container>
        <PageHeader
          breadcrumbs={breadcrumbs}
          title={t('h1', { name: page.name, cas: page.cas })}
          lead={t('lead', { name: page.name, cas: page.cas, count: page.offers, brandsCount: page.brands.length, brands: textBrands })}
        />

        <dl className="mt-10 grid gap-x-10 gap-y-5 sm:grid-cols-2 lg:grid-cols-3">
          {facts.map((f) => (
            <div key={f.label} className="min-w-0">
              <dt className="text-small text-text-secondary">{f.label}</dt>
              <dd className="mt-1 text-h4 font-medium tabular-nums text-text">{f.value}</dd>
            </div>
          ))}
        </dl>

        {page.synonyms.length ? (
          <p className="mt-8 max-w-[72ch] text-body text-text-secondary">
            {t('synonyms')}: {page.synonyms.join('; ')}
          </p>
        ) : null}

        <div className="mt-16 lg:mt-20">
          <SubstancePicker groups={groups.map((g) => ({ role: g.key, title: g.title, items: g.items }))} />
        </div>

        {page.offers > items.length ? (
          <p className="mt-8 text-body text-text-secondary">
            {t('shown', { shown: items.length, count: page.offers, cas: page.cas })}{' '}
            <Link href={`/search/?q=${encodeURIComponent(page.cas)}`} className="font-medium text-accent hover:text-accent-hover">
              {t('search')}
            </Link>
          </p>
        ) : null}

        <RequestBlock
          className="mt-20 lg:mt-28"
          title={t('requestTitle')}
          text={t('requestText')}
          docs={settings.docs}
          formType="cas_request"
          defaultMessage={t('requestMessage', { name: page.name, cas: page.cas })}
        />
      </Container>
    </>
  );
}
