import type { Metadata } from 'next';
import { X } from 'lucide-react';
import { getTranslations, setRequestLocale } from 'next-intl/server';
import type { Locale } from '@/i18n/routing';
import type { BreadcrumbItem } from '@/types/content';
import { PageHeader } from '@/components/content/PageHeader';
import { RequestBlock } from '@/components/content/RequestBlock';
import { ProductCard } from '@/components/product/ProductCard';
import { SearchBox } from '@/components/search/SearchBox';
import { TrackView } from '@/components/seo/TrackView';
import { Button } from '@/components/ui/Button';
import { Container } from '@/components/ui/Container';
import { Link } from '@/i18n/navigation';
import { getCatalogTree, getSiteSettings } from '@/lib/api';
import { cn } from '@/lib/cn';
import { getBrands } from '@/lib/content-api';
import { localizeProduct } from '@/lib/pack-label';
import { getSubstanceList } from '@/lib/product-api';
import { searchCatalog } from '@/lib/search';
import { serviceMetadata } from '@/lib/seo';

type SearchParams = Record<string, string | string[] | undefined>;
type Props = { params: Promise<{ locale: Locale }>; searchParams: Promise<SearchParams> };

const one = (v: string | string[] | undefined) => (Array.isArray(v) ? v[0] : v)?.slice(0, 100) ?? '';
const SLUG_RE = /^[a-z0-9-]{1,60}$/;

/** Результаты поиска — noindex и Disallow в robots.txt (SRCH-07, SEO-03) */
export async function generateMetadata({ params, searchParams }: Props): Promise<Metadata> {
  const { locale } = await params;
  const t = await getTranslations({ locale, namespace: 'searchPage' });
  const q = one((await searchParams).q).trim();
  return serviceMetadata(q ? t('metaTitleQuery', { q }) : t('metaTitle'));
}

export default async function SearchPage({ params, searchParams }: Props) {
  const { locale } = await params;
  setRequestLocale(locale);
  const sp = await searchParams;
  const q = one(sp.q).trim();
  const brand = SLUG_RE.test(one(sp.brand)) ? one(sp.brand) : undefined;
  const category = SLUG_RE.test(one(sp.category)) ? one(sp.category) : undefined;
  const page = Math.max(1, Number.parseInt(one(sp.page) || '1', 10) || 1);

  const t = await getTranslations('searchPage');
  const tc = await getTranslations('catalog');
  const [tree, settings, brands] = await Promise.all([getCatalogTree(locale), getSiteSettings(locale), getBrands(locale)]);
  const categoryNames = Object.fromEntries(tree.map((c) => [c.slug, c.name]));
  const result = searchCatalog({ query: q, brand, category, page, categoryNames });
  const items = result.items.map((p) => localizeProduct(p, locale));

  // Совпадения по субстанциям и брендам — отдельные группы над товарами (SRCH-01)
  const ql = (result.corrected ?? q).toLowerCase();
  const substanceHits = q.length >= 3
    ? getSubstanceList(locale).filter((s) => s.nameRu.toLowerCase().includes(ql) || s.nameEn.toLowerCase().includes(ql) || s.cas === q).slice(0, 4)
    : [];
  const brandHits = q.length >= 2 ? brands.filter((b) => b.name.toLowerCase().includes(ql)).slice(0, 4) : [];

  const href = (patch: { brand?: string | null; category?: string | null; page?: number }) => {
    const p = new URLSearchParams({ q });
    const b = patch.brand === null ? undefined : (patch.brand ?? brand);
    const c = patch.category === null ? undefined : (patch.category ?? category);
    if (b) p.set('brand', b);
    if (c) p.set('category', c);
    if (patch.page && patch.page > 1) p.set('page', String(patch.page));
    return `/search/?${p.toString()}`;
  };

  const breadcrumbs: BreadcrumbItem[] = [{ label: tc('home'), href: '/' }, { label: t('breadcrumb') }];
  const noResults = q.length >= 2 && result.total === 0 && !brand && !category;
  const chip = 'inline-flex h-10 items-center gap-2 rounded-pill px-4 text-small transition-colors md:text-body';

  return (
    <Container>
      {q ? (
        <TrackView event={noResults ? 'search_no_results' : 'site_search'} params={{ query: q, results: result.total, mode: 'page' }} />
      ) : null}
      <PageHeader
        breadcrumbs={breadcrumbs}
        title={q ? t('h1Query', { q }) : t('h1')}
        lead={q ? (noResults ? t('emptyLead') : t('found', { count: result.total })) : t('lead')}
      />
      <SearchBox key={q} size="lg" place="search_page" defaultValue={q} requestHref="#search-request" className="mt-8 max-w-[880px]" />
      {result.corrected ? (
        <p className="mt-4 text-body text-text-secondary">{t('corrected', { q: result.corrected })}</p>
      ) : null}

      {substanceHits.length || brandHits.length ? (
        <div className="mt-8 flex flex-wrap gap-x-10 gap-y-4">
          {substanceHits.length ? (
            <div>
              <h2 className="text-small text-text-secondary">{t('substances')}</h2>
              <ul className="mt-2 flex flex-wrap gap-2">
                {substanceHits.map((s) => (
                  <li key={s.slug}>
                    <Link href={`/substances/${s.slug}/`} className={cn(chip, 'bg-surface-strong text-text hover:text-accent')}>
                      {s.name}
                      <span className="text-text-secondary">{s.count}</span>
                    </Link>
                  </li>
                ))}
              </ul>
            </div>
          ) : null}
          {brandHits.length ? (
            <div>
              <h2 className="text-small text-text-secondary">{t('brands')}</h2>
              <ul className="mt-2 flex flex-wrap gap-2">
                {brandHits.map((b) => (
                  <li key={b.slug}>
                    <Link href={`/brands/${b.slug}/`} className={cn(chip, 'bg-surface-strong text-text hover:text-accent')}>
                      {b.name}
                    </Link>
                  </li>
                ))}
              </ul>
            </div>
          ) : null}
        </div>
      ) : null}

      {result.total > 0 || brand || category ? (
        <div className="mt-10 grid gap-8 lg:grid-cols-[260px_minmax(0,1fr)] xl:grid-cols-[290px_minmax(0,1fr)] 2xl:gap-10">
          {/* Фильтры со счётчиками — обычные ссылки, страница целиком в noindex */}
          <aside aria-label={t('filters')} className="flex flex-col gap-8">
            {[
              { key: 'category' as const, title: t('facetCategory'), values: result.facets.category },
              { key: 'brand' as const, title: t('facetBrand'), values: result.facets.brand },
            ].map((f) =>
              f.values.length ? (
                <section key={f.key} aria-labelledby={`facet-${f.key}`}>
                  <h2 id={`facet-${f.key}`} className="text-body font-medium text-text">
                    {f.title}
                  </h2>
                  <ul className="mt-3 flex flex-wrap gap-2 lg:flex-col lg:gap-1">
                    {f.values.slice(0, 12).map((v) => (
                      <li key={v.value}>
                        <Link
                          href={href({ [f.key]: v.selected ? null : v.value, page: 1 })}
                          aria-current={v.selected ? 'true' : undefined}
                          className={cn(
                            chip,
                            'w-full justify-between lg:h-auto lg:rounded-sm lg:px-3 lg:py-2',
                            v.selected ? 'bg-accent text-text-on-accent' : 'bg-surface-strong text-text hover:text-accent lg:bg-transparent',
                          )}
                        >
                          <span className="min-w-0 truncate">{v.label}</span>
                          <span className={cn('tabular-nums', v.selected ? 'text-text-on-accent' : 'text-text-secondary')}>{v.count}</span>
                        </Link>
                      </li>
                    ))}
                  </ul>
                </section>
              ) : null,
            )}
          </aside>

          <div className="min-w-0">
            {brand || category ? (
              <ul className="mb-6 flex flex-wrap gap-2">
                {[
                  category ? { label: categoryNames[category] ?? category, href: href({ category: null, page: 1 }) } : null,
                  brand ? { label: result.facets.brand.find((b) => b.value === brand)?.label ?? brand, href: href({ brand: null, page: 1 }) } : null,
                ]
                  .filter((x): x is { label: string; href: string } => !!x)
                  .map((x) => (
                    <li key={x.href}>
                      <Link href={x.href} aria-label={tc('removeFilter', { label: x.label })} className={cn(chip, 'bg-surface-strong text-text hover:text-accent')}>
                        {x.label}
                        <X aria-hidden size={16} strokeWidth={1.5} />
                      </Link>
                    </li>
                  ))}
              </ul>
            ) : null}

            {result.items.length ? (
              <ul className="grid gap-3 sm:grid-cols-2 md:gap-6 xl:grid-cols-3">
                {items.map((p) => (
                  <li key={p.id}>
                    <ProductCard product={p} size="md" place="search" />
                  </li>
                ))}
              </ul>
            ) : (
              <p className="text-body text-text-secondary">{t('noFiltered')}</p>
            )}

            {result.pageCount > 1 ? (
              <nav aria-label={tc('pagination')} className="mt-10 flex flex-wrap items-center gap-3">
                {result.page > 1 ? (
                  <Button href={href({ page: result.page - 1 })} variant="menu" size="s">
                    {tc('prev')}
                  </Button>
                ) : null}
                <span className="text-small text-text-secondary">{t('page', { page: result.page, total: result.pageCount })}</span>
                {result.page < result.pageCount ? (
                  <Button href={href({ page: result.page + 1 })} variant="menu" size="s">
                    {tc('next')}
                  </Button>
                ) : null}
              </nav>
            ) : null}
          </div>
        </div>
      ) : null}

      {!q ? (
        <section aria-labelledby="search-sections" className="mt-12">
          <h2 id="search-sections" className="text-h4 font-medium text-text">
            {t('sections')}
          </h2>
          <ul className="mt-4 flex flex-wrap gap-2">
            {tree.map((c) => (
              <li key={c.slug}>
                <Button href={c.href} variant="menu" size="s">
                  {c.name}
                </Button>
              </li>
            ))}
          </ul>
        </section>
      ) : null}

      {/* Пустая выдача → заявка с подставленным запросом (SC-03, SRCH-06) */}
      <RequestBlock
        id="search-request"
        className="mt-16 lg:mt-20"
        title={noResults ? t('requestTitleEmpty') : t('requestTitle')}
        text={t('requestText')}
        docs={settings.docs}
        formType={noResults ? 'search_no_results' : 'search_request'}
        defaultMessage={q ? t('requestMessage', { q }) : ''}
      />
    </Container>
  );
}
