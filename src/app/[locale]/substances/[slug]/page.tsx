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
import { getSiteSettings } from '@/lib/api';
import { getSubstancePage } from '@/lib/product-api';
import { pageMetadata, SITE_URL } from '@/lib/seo';

type Props = { params: Promise<{ locale: Locale; slug: string }> };

/** Метатеги по шаблону ТЗ 10.2; index — при ≥ 3 позициях и тексте (ТЗ 4.1) */
export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { locale, slug } = await params;
  const data = await getSubstancePage(slug);
  if (!data) return {};
  const t = await getTranslations({ locale, namespace: 'substancePage.meta' });
  const s = data.substance;
  const impurities = data.items.filter((p) => p.substance?.role !== 'api').length;
  return pageMetadata({
    locale,
    path: `/substances/${s.slug}/`,
    title: t('title', { name: s.nameRu }),
    description: t('description', { name: s.nameRu, count: impurities, brands: data.brands.slice(0, 4).join(', ') }),
    index: data.indexable,
  });
}

export default async function SubstancePage({ params }: Props) {
  const { locale, slug } = await params;
  setRequestLocale(locale);
  const [data, settings] = await Promise.all([getSubstancePage(slug), getSiteSettings()]);
  if (!data) notFound();
  const t = await getTranslations('substancePage');
  const tc = await getTranslations('catalog');
  const s = data.substance;
  const path = `/substances/${s.slug}/`;

  const breadcrumbs: BreadcrumbItem[] = [
    { label: tc('home'), href: '/' },
    { label: t('list.breadcrumb'), href: '/substances/' },
    { label: s.nameRu },
  ];

  const facts = [
    { label: t('facts.inn'), value: s.nameEn },
    ...(s.cas ? [{ label: 'CAS', value: s.cas }] : []),
    ...(s.formula ? [{ label: t('facts.formula'), value: <Formula value={s.formula} /> }] : []),
    ...(s.molecularWeight ? [{ label: t('facts.mw'), value: `${s.molecularWeight} г/моль` }] : []),
    { label: t('facts.items'), value: String(data.items.length) },
    { label: t('facts.brands'), value: data.brands.join(', ') },
  ];

  return (
    <>
      <JsonLd data={breadcrumbsLd(breadcrumbs, SITE_URL, locale, path)} />
      <Container>
        <PageHeader breadcrumbs={breadcrumbs} title={t('h1', { name: s.nameRu })} lead={s.description?.[0]} />

        <dl className="mt-10 grid gap-x-10 gap-y-5 sm:grid-cols-2 lg:grid-cols-3 2xl:grid-cols-6">
          {facts.map((f) => (
            <div key={f.label} className="min-w-0">
              <dt className="text-small text-text-secondary">{f.label}</dt>
              <dd className="mt-1 text-h4 font-medium tabular-nums text-text">{f.value}</dd>
            </div>
          ))}
        </dl>

        <div className="mt-16 lg:mt-20">
          <SubstancePicker
            groups={data.groups.map((g) => ({ role: g.role, title: t(`groups.${g.role}`), items: g.items }))}
          />
        </div>

        {s.description && s.description.length > 1 ? (
          <section aria-labelledby="substance-about" className="mt-20 max-w-[72ch] lg:mt-28">
            <h2 id="substance-about" className="text-h3 font-medium text-text">
              {t('about', { name: s.nameRu })}
            </h2>
            <div className="mt-6 flex flex-col gap-4 text-body text-text md:text-lg">
              {s.description.slice(1).map((p) => (
                <p key={p.slice(0, 32)}>{p}</p>
              ))}
              {s.synonyms?.length ? (
                <p className="text-body text-text-secondary">
                  {t('synonyms')}: {s.synonyms.join('; ')}
                </p>
              ) : null}
            </div>
          </section>
        ) : null}

        <RequestBlock
          className="mt-20 lg:mt-28"
          title={t('requestTitle', { name: s.nameRu })}
          text={t('requestText')}
          docs={settings.docs}
          formType="substance_request"
          defaultMessage={t('requestMessage', { name: s.nameRu, cas: s.cas ?? '' })}
        />
      </Container>
    </>
  );
}
