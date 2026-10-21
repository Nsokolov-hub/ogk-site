import type { Metadata } from 'next';
import { notFound } from 'next/navigation';
import { getTranslations, setRequestLocale } from 'next-intl/server';
import type { Locale } from '@/i18n/routing';
import { ActiveFilters } from '@/components/catalog/ActiveFilters';
import { CatalogFilters } from '@/components/catalog/CatalogFilters';
import { CategoryNav } from '@/components/catalog/CategoryNav';
import { CategorySections } from '@/components/catalog/CategorySections';
import { MobileFilters } from '@/components/catalog/MobileFilters';
import { ProductListing } from '@/components/catalog/ProductListing';
import { SortControl } from '@/components/catalog/SortControl';
import { Breadcrumbs } from '@/components/layout/Breadcrumbs';
import { breadcrumbsLd, faqLd, JsonLd } from '@/components/seo/JsonLd';
import { Container } from '@/components/ui/Container';
import { Link } from '@/i18n/navigation';
import { getSiteSettings } from '@/lib/api';
import { catalogHref, countSelected, parseCatalogQuery, type SearchParams } from '@/lib/catalog';
import { getCatalogListing } from '@/lib/catalog-api';
import { getCategoryPage } from '@/lib/category-page';
import { cn } from '@/lib/cn';

type Props = {
  params: Promise<{ locale: Locale; slug?: string[] }>;
  searchParams: Promise<SearchParams>;
};

async function load(locale: Locale, slug: string[]) {
  const t = await getTranslations({ locale, namespace: 'catalog' });
  return getCategoryPage(slug, locale, { home: t('home'), catalog: t('catalog'), categories: t('categories') });
}

/**
 * SEO (ТЗ URL-06, URL-08): фильтры и сортировка — noindex, follow и canonical на категорию;
 * пагинация — canonical на себя и «— страница N» в Title.
 */
export async function generateMetadata({ params, searchParams }: Props): Promise<Metadata> {
  const { locale, slug = [] } = await params;
  const data = await load(locale, slug);
  if (!data) return {};
  const t = await getTranslations({ locale, namespace: 'catalog' });
  const q = parseCatalogQuery(await searchParams);
  const filtered = countSelected(q.filters) > 0 || q.sort !== 'popular';
  const base = data.href;
  const localized = locale === 'ru' ? base : `/${locale}${base}`;
  const canonical = !filtered && q.page > 1 ? `${localized}?page=${q.page}` : localized;
  const title = !filtered && q.page > 1 ? `${data.content.title} ${t('pageTitle', { n: q.page })}` : data.content.title;

  return {
    title,
    description: data.content.description,
    alternates: { canonical, languages: { ru: base, en: `/en${base}`, 'x-default': base } },
    robots: filtered ? { index: false, follow: true } : undefined,
    openGraph: { type: 'website', url: canonical, siteName: 'ОГК-ХИМ', title, description: data.content.description },
  };
}

export default async function CatalogPage({ params, searchParams }: Props) {
  const { locale, slug = [] } = await params;
  setRequestLocale(locale);
  const data = await load(locale, slug);
  if (!data) notFound();

  const query = parseCatalogQuery(await searchParams);
  const [listing, settings] = await Promise.all([
    getCatalogListing({ path: slug, filters: query.filters, sort: query.sort, page: query.page, facetKeys: data.content.facets, locale }),
    getSiteSettings(),
  ]);
  if (query.page > listing.pageCount && listing.total > 0) notFound();

  // Ключ выборки: при смене фильтров, сортировки или страницы клиентские блоки начинают с чистого состояния
  const queryKey = catalogHref('', query) || 'all';
  const ld: Record<string, unknown>[] = [breadcrumbsLd(data.breadcrumbs, settings.siteUrl, locale, data.href)];
  if (data.content.faq?.length) ld.push(faqLd(data.content.faq));

  return (
    <>
      <JsonLd data={ld} />
      <Container className="pt-24 lg:pt-[150px]">
        <Breadcrumbs items={data.breadcrumbs} />

        <div className="mt-6 flex flex-wrap items-end justify-between gap-x-6 gap-y-4">
          <h1 className="text-title font-medium text-text">{data.content.h1}</h1>
          <SortControl key={`sort-${queryKey}`} basePath={data.href} query={query} />
        </div>
        <p className="mt-3 max-w-[880px] text-body text-text-secondary">{data.content.intro}</p>

        {/* Разделы на телефоне и планшете — лентой; на десктопе они в боковой панели */}
        <ul className="scroll-row -mx-4 mt-6 gap-2 px-4 md:-mx-6 md:px-6 lg:hidden">
          {data.nav.items.map((item) => (
            <li key={item.href}>
              <Link
                href={item.href}
                aria-current={item.active ? 'page' : undefined}
                className={cn(
                  'inline-flex h-9 items-center whitespace-nowrap rounded-pill border px-4 text-small transition-colors',
                  item.active ? 'border-accent bg-accent text-text-on-accent' : 'border-border text-text hover:border-accent hover:text-accent',
                )}
              >
                {item.label}
              </Link>
            </li>
          ))}
        </ul>

        <div className="mt-6 grid gap-8 lg:mt-10 lg:grid-cols-[260px_minmax(0,1fr)] xl:grid-cols-[290px_minmax(0,1fr)] 2xl:gap-10">
          <aside className="hidden lg:block">
            <div className="sticky top-24 max-h-[calc(100svh-7rem)] overflow-y-auto overscroll-contain pr-3 [scrollbar-width:thin]">
              <CategoryNav nav={data.nav} />
              <CatalogFilters key={`filters-${queryKey}`} facets={listing.facets} basePath={data.href} query={query} />
            </div>
          </aside>

          <div className="min-w-0">
            <div className="flex flex-wrap items-center gap-3">
              {listing.facets.length ? (
                <MobileFilters
                  key={`mobile-${queryKey}`}
                  facets={listing.facets}
                  basePath={data.href}
                  query={query}
                  nav={data.nav}
                  className="lg:hidden"
                />
              ) : null}
              <ActiveFilters facets={listing.facets} basePath={data.href} query={query} />
            </div>
            <ProductListing key={`list-${queryKey}`} initial={listing} path={slug} basePath={data.href} query={query} />
          </div>
        </div>

        <CategorySections data={data} docs={settings.docs} />
      </Container>
    </>
  );
}
