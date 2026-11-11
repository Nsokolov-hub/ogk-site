import type { Metadata } from 'next';
import { notFound } from 'next/navigation';
import { getTranslations, setRequestLocale } from 'next-intl/server';
import type { Locale } from '@/i18n/routing';
import type { BreadcrumbItem } from '@/types/content';
import { CasLinks } from '@/components/content/CasLinks';
import { Formula } from '@/components/content/Formula';
import { PageHeader } from '@/components/content/PageHeader';
import { RequestBlock } from '@/components/content/RequestBlock';
import { SubstancePicker } from '@/components/product/SubstancePicker';
import { breadcrumbsLd, JsonLd } from '@/components/seo/JsonLd';
import { Container } from '@/components/ui/Container';
import { Link, permanentRedirect } from '@/i18n/navigation';
import { getSiteSettings } from '@/lib/api';
import { getCasPage } from '@/lib/product-api';
import { CAS_EN_INDEXED, pageMetadata, SITE_URL } from '@/lib/seo';

type Props = { params: Promise<{ locale: Locale; cas: string }> };

const BRANDS_IN_TEXT = 5;
const BRANDS_IN_FACTS = 8;
/** Длиннее — название в title обрезаем по слову: CAS и число позиций должны остаться видны в выдаче */
const TITLE_NAME = 60;

/** Название для title: целиком, если короткое; иначе короткий синоним или начало названия по слову */
function titleName(name: string, synonyms: string[]): string {
  if (name.length <= TITLE_NAME) return name;
  const short = synonyms.filter((s) => s.length <= TITLE_NAME).sort((a, b) => a.length - b.length)[0];
  if (short) return short;
  const cut = name.slice(0, TITLE_NAME);
  const space = cut.lastIndexOf(' ');
  return `${(space > 30 ? cut.slice(0, space) : cut).replace(/[\s,;(\-]+$/, '')}…`;
}

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
  // Русское название — первым: так ищут в Яндексе; латинское остаётся в описании и на странице
  const ru = locale === 'ru' && page.nameRu ? page.nameRu : null;
  const name = ru ?? titleName(page.name, page.synonyms);
  return pageMetadata({
    locale,
    path: `/cas/${page.cas}/`,
    title: t('meta.title', { name, cas: page.cas, count: page.offers }),
    description: t('meta.description', { name: ru ? `${ru} (${page.name})` : page.name, cas: page.cas, count: page.offers, brands }),
    hasEn: CAS_EN_INDEXED,
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

  const displayName = locale === 'ru' && page.nameRu ? `${page.nameRu} (${page.name})` : page.name;
  const breadcrumbs: BreadcrumbItem[] = [
    { label: tc('home'), href: '/' },
    { label: t('breadcrumb'), href: '/cas/' },
    { label: displayName },
  ];
  const textBrands =
    page.brands.slice(0, BRANDS_IN_TEXT).join(', ') +
    (page.brands.length > BRANDS_IN_TEXT ? ` ${t('facts.more', { count: page.brands.length - BRANDS_IN_TEXT })}` : '');
  const factBrands =
    page.brands.slice(0, BRANDS_IN_FACTS).join(', ') +
    (page.brands.length > BRANDS_IN_FACTS ? ` ${t('facts.more', { count: page.brands.length - BRANDS_IN_FACTS })}` : '');

  const facts = [
    ...(locale === 'ru' && page.nameRu ? [{ label: t('facts.nameRu'), value: page.nameRu }] : []),
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
          title={t('h1', { name: displayName, cas: page.cas })}
          lead={t('lead', { name: displayName, cas: page.cas, count: page.offers, brandsCount: page.brands.length, brands: textBrands })}
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

        {data.neighbours.length ? (
          <section aria-labelledby="cas-neighbours" className="mt-20 lg:mt-28">
            <div className="flex flex-wrap items-end justify-between gap-4">
              <h2 id="cas-neighbours" className="text-h3 font-medium text-text">
                {t('neighbours')}
              </h2>
              <Link href={`/cas/letter/${page.letter}/`} className="text-body font-medium text-accent transition-colors hover:text-accent-hover">
                {page.letter === '0' ? t('letterOther') : t('letterAll', { letter: page.letter.toUpperCase() })}
              </Link>
            </div>
            <div className="mt-6">
              <CasLinks items={data.neighbours} locale={locale} />
            </div>
          </section>
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
