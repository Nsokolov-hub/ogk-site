import type { Metadata } from 'next';
import Image from 'next/image';
import { notFound } from 'next/navigation';
import { ArrowRight } from 'lucide-react';
import { getTranslations, setRequestLocale } from 'next-intl/server';
import type { Locale } from '@/i18n/routing';
import type { BreadcrumbItem } from '@/types/content';
import { FaqSection } from '@/components/content/FaqSection';
import { LinkChips } from '@/components/content/LinkChips';
import { PageHeader } from '@/components/content/PageHeader';
import { RequestBlock } from '@/components/content/RequestBlock';
import { ProductCard } from '@/components/product/ProductCard';
import { breadcrumbsLd, faqLd, JsonLd } from '@/components/seo/JsonLd';
import { TrackView } from '@/components/seo/TrackView';
import { Button } from '@/components/ui/Button';
import { Container } from '@/components/ui/Container';
import { Link } from '@/i18n/navigation';
import { getSiteSettings } from '@/lib/api';
import { previewParam } from '@/lib/content';
import { getBrandPage, getBrands } from '@/lib/content-api';
import { pageMetadata, SITE_URL } from '@/lib/seo';

type Props = { params: Promise<{ locale: Locale; slug: string }>; searchParams: Promise<{ preview?: string }> };

export async function generateMetadata({ params, searchParams }: Props): Promise<Metadata> {
  const { locale, slug } = await params;
  const data = await getBrandPage(slug, locale, previewParam((await searchParams).preview));
  if (!data) return {};
  const b = data.brand;
  return pageMetadata({ locale, path: `/brands/${b.slug}/`, title: b.title, description: b.description, hasEn: b.hasEn });
}

export default async function BrandPage({ params, searchParams }: Props) {
  const { locale, slug } = await params;
  setRequestLocale(locale);
  const [data, brands, settings] = await Promise.all([getBrandPage(slug, locale, previewParam((await searchParams).preview)), getBrands(locale), getSiteSettings(locale)]);
  if (!data) notFound();
  const t = await getTranslations('brands');
  const tc = await getTranslations('catalog');
  const b = data.brand;
  const path = `/brands/${b.slug}/`;

  const breadcrumbs: BreadcrumbItem[] = [
    { label: tc('home'), href: '/' },
    { label: t('list.breadcrumb'), href: '/brands/' },
    { label: b.name },
  ];
  const ld: Record<string, unknown>[] = [breadcrumbsLd(breadcrumbs, SITE_URL, locale, path)];
  if (b.faq?.length) ld.push(faqLd(b.faq));

  const facts = [
    ...(b.country ? [{ label: t('page.country'), value: b.country }] : []),
    { label: t('page.items'), value: data.count ? String(data.count) : t('page.onRequest') },
    { label: t('page.packaging'), value: b.customPackaging ? t('page.packagingCustom') : t('page.packagingFixed') },
  ];

  const otherBrands = brands.filter((x) => x.slug !== b.slug && x.wave === 1).map((x) => ({ label: x.name, href: `/brands/${x.slug}/` }));
  const h2 = 'text-h3 font-medium text-text';

  return (
    <>
      <JsonLd data={ld} />
      <TrackView event="brand_view" params={{ brand: b.name }} />
      <Container>
        <PageHeader
          breadcrumbs={breadcrumbs}
          title={b.h1}
          lead={b.intro}
          aside={
            <div className="grid h-36 w-full place-items-center rounded-block bg-surface px-10 sm:w-80 lg:h-44">
              {b.logo ? (
                <Image src={b.logo} alt={t('page.logoAlt', { brand: b.name })} width={212} height={172} unoptimized priority className="h-24 w-auto object-contain lg:h-28" />
              ) : (
                <span className="text-h2 font-medium text-text">{b.name}</span>
              )}
            </div>
          }
        />

        <dl className="mt-10 grid gap-x-10 gap-y-5 sm:grid-cols-3 lg:max-w-[900px]">
          {facts.map((f) => (
            <div key={f.label}>
              <dt className="text-small text-text-secondary">{f.label}</dt>
              <dd className="mt-1 text-h4 font-medium text-text">{f.value}</dd>
            </div>
          ))}
        </dl>

        <div className="mt-20 flex flex-col gap-20 lg:mt-28 lg:gap-28">
          {/* Разделы каталога с товарами бренда */}
          <section aria-labelledby="brand-groups">
            <h2 id="brand-groups" className={h2}>
              {t('page.groups', { brand: b.name })}
            </h2>
            <ul className="mt-6 flex flex-wrap gap-2">
              {b.groups.map((g) => {
                const count = data.categories
                  .filter((c) => `/catalog/${c.slug}/`.startsWith(g.href))
                  .reduce((n, c) => n + c.count, 0);
                return (
                  <li key={g.href}>
                    <Link
                      href={g.href}
                      className="inline-flex h-11 items-center gap-2 rounded-pill bg-surface-strong px-5 text-body text-text transition-colors hover:text-accent"
                    >
                      {g.label}
                      {count ? <span className="text-small tabular-nums text-text-secondary">{count}</span> : null}
                    </Link>
                  </li>
                );
              })}
            </ul>
          </section>

          {data.products.length ? (
            <section aria-labelledby="brand-products">
              <div className="flex flex-wrap items-end justify-between gap-4">
                <h2 id="brand-products" className={h2}>
                  {t('page.popular', { brand: b.name })}
                </h2>
                <Link
                  href={`/catalog/?brand=${b.slug}`}
                  className="inline-flex items-center gap-2 text-body font-medium text-accent transition-colors hover:text-accent-hover"
                >
                  {t('page.allItems', { count: data.count })}
                  <ArrowRight aria-hidden size={18} strokeWidth={1.5} />
                </Link>
              </div>
              <ul className="mt-6 grid gap-3 sm:grid-cols-2 md:gap-6 lg:grid-cols-3 xl:grid-cols-4">
                {data.products.map((p) => (
                  <li key={p.id}>
                    <ProductCard product={p} size="sm" place="list" />
                  </li>
                ))}
              </ul>
            </section>
          ) : (
            <section aria-labelledby="brand-products" className="rounded-block bg-surface p-6 md:p-10">
              <h2 id="brand-products" className={h2}>
                {t('page.noItemsTitle', { brand: b.name })}
              </h2>
              <p className="mt-3 max-w-[60ch] text-body text-text-secondary md:text-lg">{t('page.noItemsText')}</p>
              <Button href="#request" size="m" className="mt-6">
                {t('page.sendList')}
              </Button>
            </section>
          )}

          <section aria-labelledby="brand-about" className="max-w-[72ch]">
            <h2 id="brand-about" className={h2}>
              {t('page.about', { brand: b.name })}
            </h2>
            <div className="mt-6 flex flex-col gap-4 text-body text-text md:text-lg">
              {b.text.map((p) => (
                <p key={p.slice(0, 32)}>{p}</p>
              ))}
            </div>
          </section>

          {b.faq?.length ? <FaqSection id="brand-faq" title={t('page.faq')} items={b.faq} /> : null}

          <RequestBlock
            title={t('page.requestTitle', { brand: b.name })}
            text={t('page.requestText')}
            docs={settings.docs}
            formType="brand_request"
            defaultMessage={t('page.requestMessage', { brand: b.name })}
          />

          <LinkChips id="brand-others" title={t('page.others')} items={otherBrands} />
        </div>
      </Container>
    </>
  );
}
