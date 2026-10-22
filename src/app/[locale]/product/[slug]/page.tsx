import type { Metadata } from 'next';
import type { ReactNode } from 'react';
import { notFound } from 'next/navigation';
import { ArrowRight, TriangleAlert } from 'lucide-react';
import { getTranslations, setRequestLocale } from 'next-intl/server';
import type { Locale } from '@/i18n/routing';
import type { BreadcrumbItem } from '@/types/content';
import { ProductTable } from '@/components/catalog/ProductTable';
import { FaqSection } from '@/components/content/FaqSection';
import { Formula } from '@/components/content/Formula';
import { RequestBlock } from '@/components/content/RequestBlock';
import { Breadcrumbs } from '@/components/layout/Breadcrumbs';
import { ProductCard } from '@/components/product/ProductCard';
import { ProductImage } from '@/components/product/ProductImage';
import { CopyButton } from '@/components/product/detail/CopyButton';
import { DocumentList } from '@/components/product/detail/DocumentList';
import { ProductOrderPanel } from '@/components/product/detail/ProductOrderPanel';
import { ProductTabs } from '@/components/product/detail/ProductTabs';
import { breadcrumbsLd, faqLd, JsonLd, productLd } from '@/components/seo/JsonLd';
import { TrackView } from '@/components/seo/TrackView';
import { Container } from '@/components/ui/Container';
import { Link } from '@/i18n/navigation';
import { getSiteSettings } from '@/lib/api';
import { cn } from '@/lib/cn';
import { getProductPage, toPreview } from '@/lib/product-api';
import { absoluteUrl, pageMetadata, SITE_URL } from '@/lib/seo';

type Props = { params: Promise<{ locale: Locale; slug: string }> };

/** Название в Title — не длиннее ~70 знаков, по границе слова */
function shortName(name: string, max = 70) {
  if (name.length <= max) return name;
  const cut = name.slice(0, max);
  return `${cut.slice(0, cut.lastIndexOf(' ')).replace(/[,;(]+$/, '')}…`;
}

const COLD = new Set(['2-8', '-20', '-80']);

/** Метатеги по шаблону ТЗ 10.2 */
export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { locale, slug } = await params;
  const data = await getProductPage(slug, locale);
  if (!data) return {};
  const t = await getTranslations({ locale, namespace: 'productPage.meta' });
  const p = data.product;
  const numberLabel = p.cardType === 'equipment' ? 'P/N' : t('number');
  const title = p.cas
    ? t('title', { name: shortName(p.name), brand: p.brand.name, number: p.catalogNumber, cas: p.cas })
    : t('titleNoCas', { name: shortName(p.name), brand: p.brand.name, number: p.catalogNumber, numberLabel });
  const ids = [`${p.brand.name}`, `${numberLabel} ${p.catalogNumber}`, p.cas ? `CAS ${p.cas}` : null, p.formula ? p.formula : null]
    .filter(Boolean)
    .join(', ');
  const description = t('description', {
    name: shortName(p.name, 90),
    ids,
    logistics: p.storage && COLD.has(p.storage) ? t('cold') : t('ambient'),
  });

  return pageMetadata({ locale, path: `/product/${p.slug}/`, title, description, index: p.indexable, hasEn: p.hasEn });
}

export default async function ProductPage({ params }: Props) {
  const { locale, slug } = await params;
  setRequestLocale(locale);
  const [data, settings] = await Promise.all([getProductPage(slug, locale), getSiteSettings(locale)]);
  if (!data) notFound();

  const t = await getTranslations('productPage');
  const tc = await getTranslations('catalog');
  const { product: p, categories, substance } = data;
  const preview = toPreview(p);
  const path = `/product/${p.slug}/`;

  const breadcrumbs: BreadcrumbItem[] = [
    { label: tc('home'), href: '/' },
    { label: tc('catalog'), href: '/catalog/' },
    ...categories.map((c) => ({ label: c.name, href: c.href })),
    { label: p.name },
  ];

  const numberLabel =
    p.cardType === 'equipment' ? t('ids.partNumber') : p.categorySlug === 'biological-standards' ? t('ids.strainCode') : t('ids.catalogNumber');
  const productLabel = `${p.name}, ${p.brand.name} ${p.catalogNumber}`;
  // Что это за позиция, если нет русского названия: роль по субстанции или раздел каталога
  const deepest = categories.at(-1);
  const brandNamedSub = categories.length === 2 && categories[0].slug === 'reference-standards' && deepest?.slug !== 'impurity-standards';
  const kindLabel =
    substance && p.substance
      ? `${t(`roles.${p.substance.role}`)}: ${substance.name.toLowerCase()}`
      : (brandNamedSub ? categories[0].name : deepest?.name) ?? '';
  const ld: Record<string, unknown>[] = [
    breadcrumbsLd(breadcrumbs, SITE_URL, locale, path),
    productLd({
      url: absoluteUrl(locale, path),
      name: p.name,
      sku: p.catalogNumber,
      brand: p.brand.name,
      description: p.description[0],
      image: p.image ? `${SITE_URL}${p.image.src}` : undefined,
      cas: p.cas,
      category: categories.at(-1)?.name,
    }),
  ];
  if (p.faq?.length) ld.push(faqLd(p.faq));

  // Ключевые идентификаторы рядом с изображением (ТЗ 5.4); пустые не выводим
  const ids: { label: string; value: ReactNode; copy?: string }[] = [
    { label: numberLabel, value: p.catalogNumber, copy: p.catalogNumber },
    ...(p.cas ? [{ label: t('ids.cas'), value: p.cas, copy: p.cas }] : []),
    ...(p.formula ? [{ label: t('ids.formula'), value: <Formula value={p.formula} /> }] : []),
    ...(p.molecularWeight ? [{ label: t('ids.mw'), value: t('ids.mwValue', { value: p.molecularWeight }) }] : []),
    ...(p.purity ? [{ label: t('ids.purity'), value: p.purity }] : []),
    ...(p.storage ? [{ label: t('ids.storage'), value: tc(`values.storage.${p.storage}`) }] : []),
  ];

  // Технические данные: все заполненные поля типа карточки (ТЗ 5.2)
  const specs: { label: string; value: ReactNode }[] = [
    { label: t('ids.brand'), value: p.brand.name },
    { label: numberLabel, value: p.catalogNumber },
    ...(p.cas ? [{ label: t('ids.cas'), value: p.cas }] : []),
    ...(p.altCas?.length ? [{ label: t('ids.altCas'), value: p.altCas.join(', ') }] : []),
    ...(p.formula ? [{ label: t('ids.formula'), value: <Formula value={p.formula} /> }] : []),
    ...(p.molecularWeight ? [{ label: t('ids.mw'), value: t('ids.mwValue', { value: p.molecularWeight }) }] : []),
    ...(p.iupacName ? [{ label: t('ids.iupac'), value: <span className="chem-wrap">{p.iupacName}</span> }] : []),
    ...(p.synonyms?.length ? [{ label: t('ids.synonyms'), value: p.synonyms.join('; ') }] : []),
    ...(p.purity ? [{ label: t('ids.purity'), value: p.purity }] : []),
    ...(p.monograph ? [{ label: t('ids.monograph'), value: p.monograph }] : []),
    ...(substance && p.substance
      ? [
          {
            label: t('ids.substance'),
            value: (
              <Link href={`/substances/${substance.slug}/`} className="text-accent underline-offset-2 hover:underline">
                {substance.name} — {tc(`values.type.${p.substance.role}`).toLowerCase()}
              </Link>
            ),
          },
        ]
      : []),
    ...(p.attributes?.purpose?.length
      ? [{ label: t('ids.purpose'), value: p.attributes.purpose.map((v) => tc(`values.purpose.${v}`)).join(', ') }]
      : []),
    ...(p.specs ?? []),
    ...(p.packagings.length ? [{ label: t('ids.packagings'), value: p.packagings.map((x) => x.label).join(', ') }] : []),
    ...(p.customPackaging ? [{ label: t('ids.customPackaging'), value: t('ids.customPackagingValue') }] : []),
    ...(p.storage ? [{ label: t('ids.storage'), value: tc(`values.storage.${p.storage}`) }] : []),
    ...(p.shipping ? [{ label: t('ids.shipping'), value: t(`shipping.${p.shipping}`) }] : []),
    ...(p.dangerousGoods ? [{ label: t('ids.dangerous'), value: t('ids.yes') }] : []),
  ];

  const description = (
    <div className="flex max-w-[72ch] flex-col gap-4 text-body text-text md:text-lg">
      {p.description.map((para) => (
        <p key={para.slice(0, 32)}>{para}</p>
      ))}
    </div>
  );
  const specsTable = (
    <dl className="max-w-[880px] overflow-hidden rounded-field">
      {specs.map((row, i) => (
        <div
          key={`${row.label}-${i}`}
          className={cn('grid gap-1 px-4 py-3 sm:grid-cols-[minmax(0,2fr)_minmax(0,3fr)] sm:gap-6 md:px-5', i % 2 === 0 ? 'bg-surface' : 'bg-transparent')}
        >
          <dt className="text-small text-text-secondary sm:text-body">{row.label}</dt>
          <dd className="text-body tabular-nums text-text">{row.value}</dd>
        </div>
      ))}
    </dl>
  );

  const h2 = 'text-h3 font-medium text-text';
  const isChemical = p.cardType === 'standard';

  return (
    <>
      <JsonLd data={ld} />
      <TrackView event="product_view" params={{ sku: p.catalogNumber, brand: p.brand.name, category: p.categorySlug }} />
      <Container className="pt-24 lg:pt-[150px]">
        <Breadcrumbs items={breadcrumbs} className="[&_li:last-child]:min-w-0 [&_li:last-child>span]:line-clamp-1" />

        {/* H1 = название товара; под ним — что это и чьё (бренд — ссылка на страницу бренда) */}
        <div className="mt-6 max-w-[1100px]">
          <h1 className="chem-wrap text-title font-medium text-text">{p.name}</h1>
          <p className="mt-3 text-lead text-text-secondary">
            {p.brand.slug === 'various' ? (
              p.brand.name
            ) : (
              <Link href={`/brands/${p.brand.slug}/`} className="text-text underline-offset-4 transition-colors hover:text-accent hover:underline">
                {p.brand.name}
              </Link>
            )}
            {' · '}
            {p.nameRu ?? kindLabel}
          </p>
        </div>

        {p.discontinued ? (
          <p role="note" className="mt-6 flex max-w-[880px] gap-3 rounded-field bg-warning/10 p-4 text-body text-text">
            <TriangleAlert aria-hidden size={22} strokeWidth={1.5} className="shrink-0 text-warning" />
            <span>
              <strong className="font-medium">{t('discontinued')}.</strong> {t('discontinuedText')}
            </span>
          </p>
        ) : null}

        <div className="mt-8 grid gap-8 lg:mt-10 lg:grid-cols-[minmax(0,5fr)_minmax(0,7fr)] lg:gap-12 2xl:gap-16">
          <div className="min-w-0">
            <ProductImage product={preview} sizes="(min-width: 1024px) 40vw, 90vw" priority className="mx-auto w-full max-w-[440px] rounded-block lg:max-w-none" />
          </div>

          <div className="flex min-w-0 flex-col gap-6">
            <dl className="grid gap-x-8 gap-y-4 sm:grid-cols-2">
              {ids.map((row) => (
                <div key={row.label} className="min-w-0">
                  <dt className="text-small text-text-secondary">{row.label}</dt>
                  <dd className="mt-1 flex items-center gap-1 text-h4 font-medium tabular-nums text-text">
                    <span id={row.copy ? `copy-${row.copy}` : undefined} className="chem-wrap">
                      {row.value}
                    </span>
                    {row.copy ? <CopyButton value={row.copy} label={row.label} /> : null}
                  </dd>
                </div>
              ))}
            </dl>

            {p.customPackaging ? <p className="text-body text-accent">{t('anyPackaging')}</p> : null}

            <ProductOrderPanel product={preview} phone={settings.phone} />
          </div>
        </div>

        {/* Описание и технические данные + документы */}
        <div className="mt-20 grid gap-12 lg:mt-28 lg:grid-cols-[minmax(0,8fr)_minmax(0,4fr)] lg:gap-12">
          <section aria-label={t('tabs.label')} className="min-w-0">
            <ProductTabs
              label={t('tabs.label')}
              tabs={[
                { id: 'description', label: t('tabs.description'), content: description },
                { id: 'specs', label: t('tabs.specs'), content: specsTable },
              ]}
            />
          </section>
          <section aria-labelledby="product-docs" className="min-w-0">
            <h2 id="product-docs" className="text-h4 font-medium text-text">
              {t('docs.title')}
            </h2>
            <div className="mt-5">
              <DocumentList documents={p.documents} productLabel={productLabel} sku={p.catalogNumber} withBatchCoa={isChemical} />
            </div>
          </section>
        </div>

        <div className="mt-20 flex flex-col gap-20 lg:mt-28 lg:gap-28">
          {substance && data.sameSubstance.length ? (
            <section aria-labelledby="product-substance">
              <div className="flex flex-wrap items-end justify-between gap-4">
                <h2 id="product-substance" className={h2}>
                  {t('sections.substance', { name: substance.name })}
                </h2>
                <Link
                  href={`/substances/${substance.slug}/`}
                  className="inline-flex items-center gap-2 text-body font-medium text-accent transition-colors hover:text-accent-hover"
                >
                  {t('sections.substanceAll', { count: data.sameSubstanceTotal + 1 })}
                  <ArrowRight aria-hidden size={18} strokeWidth={1.5} />
                </Link>
              </div>
              <div className="mt-6">
                <ProductTable items={data.sameSubstance} caption={t('sections.substance', { name: substance.name })} />
              </div>
            </section>
          ) : null}

          {data.analogues.length ? (
            <section aria-labelledby="product-analogues">
              <h2 id="product-analogues" className={h2}>
                {t('sections.analogues')}
              </h2>
              <ul className="mt-6 grid gap-3 sm:grid-cols-2 md:gap-6 xl:grid-cols-4">
                {data.analogues.map((a) => (
                  <li key={a.id}>
                    <ProductCard product={a} size="sm" place="card" />
                  </li>
                ))}
              </ul>
            </section>
          ) : null}

          {data.accessories.length ? (
            <section aria-labelledby="product-accessories">
              <h2 id="product-accessories" className={h2}>
                {t('sections.accessories')}
              </h2>
              <ul className="mt-6 grid gap-3 sm:grid-cols-2 md:gap-6 xl:grid-cols-4">
                {data.accessories.map((a) => (
                  <li key={a.id}>
                    <ProductCard product={a} size="sm" place="card" />
                  </li>
                ))}
              </ul>
            </section>
          ) : null}

          {p.faq?.length ? <FaqSection id="product-faq" title={t('sections.faq')} items={p.faq} /> : null}

          <RequestBlock
            id="product-request"
            title={t('sections.requestTitle')}
            text={t('sections.requestText')}
            docs={settings.docs}
            formType="product_request"
            defaultMessage={t('sections.requestMessage', { product: productLabel, cas: p.cas ? `, CAS ${p.cas}` : '' })}
          />
        </div>
      </Container>
    </>
  );
}

