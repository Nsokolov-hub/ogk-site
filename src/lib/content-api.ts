/**
 * Контент страниц: бренды — из API каталога (тексты страниц брендов хранятся у бренда), услуги, статьи, авторы
 * и решения — из API текстов сайта (их ведут в админке, ADM-02). Только сервер.
 */
import type { Locale } from '@/i18n/routing';
import type { ProductPreview } from '@/types/catalog';
import type { Article, Author, BrandContent, ServiceContent, SolutionContent } from '@/types/content';
import type { Schemas } from './api-types';
import { api, apiOrNull } from './backend';
import { getCatalogListing, countInScope } from './catalog-api';
import { pageContent, pageList, type PageResult } from './content';

// ── бренды ──

export interface BrandListItem extends BrandContent {
  count: number;
}

/** Бренд из API; content — тексты страницы бренда по языкам в форме BrandContent */
type ApiBrand = Omit<Schemas['BrandOut'], 'content'> & { content: { ru?: BrandContent; en?: BrandContent } };

/** Текст страницы бренда на языке страницы; без перевода остаётся русский, hasEn = false (EN-05) */
function brandContentFor(b: ApiBrand, locale: string): BrandContent | null {
  const ru = b.content.ru;
  if (!ru) return null;
  const en = b.content.en;
  const base = { ...ru, slug: b.slug, name: b.name, logo: b.logo ?? ru.logo, updatedAt: ru.updatedAt ?? b.updatedAt };
  if (locale === 'en') return en ? { ...base, ...en, slug: b.slug, hasEn: true } : { ...base, hasEn: false };
  return { ...base, hasEn: !!en };
}

/** Бренды на языке страницы; у русских отмечено, есть ли перевод (для hreflang и Sitemap) */
export async function brandsFor(locale: string): Promise<BrandListItem[]> {
  const rows = await api<ApiBrand[]>('/public/brands', undefined, { tags: ['catalog', 'brands'] });
  return rows.flatMap((b) => {
    const content = brandContentFor(b, locale);
    return content ? [{ ...content, count: b.count }] : [];
  });
}

export async function getBrands(locale: Locale): Promise<BrandListItem[]> {
  return brandsFor(locale);
}

export interface BrandPageData {
  brand: BrandContent;
  count: number;
  products: ProductPreview[];
  /** Подкатегории каталога, где представлен бренд, с числом позиций */
  categories: { slug: string; count: number }[];
}

/** preview — черновик страницы бренда из админки по подписанной ссылке (без кэша) */
export async function getBrandPage(slug: string, locale: Locale, preview?: string): Promise<BrandPageData | null> {
  const data = await apiOrNull<Omit<Schemas['BrandPage'], 'brand' | 'products'> & { brand?: ApiBrand | null; products: ProductPreview[] }>(
    `/public/brands/${encodeURIComponent(slug)}`,
    { lang: locale, preview },
    preview ? { revalidate: false } : { tags: ['catalog', `brand:${slug}`] },
  );
  if (!data?.brand) return null;
  const brand = brandContentFor(data.brand, locale);
  if (!brand) return null;
  return { brand, count: data.brand.count, products: data.products, categories: data.categories ?? [] };
}

// ── услуги ──

/** Услуги на языке страницы; у русских отмечено, есть ли перевод (для hreflang и Sitemap) */
export async function getServices(locale: Locale | string): Promise<ServiceContent[]> {
  return pageList<ServiceContent>('service', locale);
}

export async function getService(slug: string, locale: Locale, preview?: string): Promise<PageResult<ServiceContent>> {
  return pageContent<ServiceContent>('service', slug, locale, preview);
}

// ── статьи ──

export async function getArticles(locale: Locale | string): Promise<Article[]> {
  return (await pageList<Article>('article', locale)).sort((a, b) => b.publishedAt.localeCompare(a.publishedAt));
}

export async function getArticle(slug: string, locale: Locale, preview?: string): Promise<PageResult<Article>> {
  return pageContent<Article>('article', slug, locale, preview);
}

export async function getAuthor(slug: string, preview?: string): Promise<PageResult<Author>> {
  return pageContent<Author>('author', slug, 'ru', preview);
}

export async function getAuthors(): Promise<Author[]> {
  return pageList<Author>('author', 'ru');
}

// ── страницы доверия: /about/, /delivery/, /documents/, /contacts/ ──

export async function getTrustPage<T extends object>(slug: string, locale: Locale, preview?: string): Promise<PageResult<T>> {
  return pageContent<T>('trust', slug, locale, preview);
}

// ── отраслевые решения ──

export async function getSolutions(locale: Locale | string): Promise<SolutionContent[]> {
  return pageList<SolutionContent>('solution', locale);
}

export interface SolutionPageData {
  solution: SolutionContent;
  /** Число позиций в каталоге для каждой группы — по порядку групп */
  counts: number[];
  /** «Часто заказывают»: самые популярные позиции выбранных разделов */
  products: ProductPreview[];
  services: ServiceContent[];
  articles: Article[];
}

export async function getSolutionPage(
  slug: string,
  locale: Locale,
  preview?: string,
): Promise<(SolutionPageData & { preview: boolean }) | { moved: string } | null> {
  const found = await pageContent<SolutionContent>('solution', slug, locale, preview);
  if (found.moved) return { moved: found.moved };
  const solution = found.page;
  if (!solution) return null;
  const [services, articles] = await Promise.all([getServices(locale), getArticles(locale)]);
  const counts = await Promise.all(
    solution.groups.map(async (g) => (await Promise.all(g.scope.map((path) => countInScope(path.split('/'))))).reduce((a, b) => a + b, 0)),
  );
  // Популярные позиции каждого раздела подборки, затем общий топ из восьми
  const lists = await Promise.all(
    solution.featured.map((path) => getCatalogListing({ path: path.split('/'), filters: {}, sort: 'popular', page: 1, pageSize: 8, facetKeys: [], locale })),
  );
  const products = lists
    .flatMap((l) => l.items)
    .sort((a, b) => (b.popularity ?? 0) - (a.popularity ?? 0))
    .filter((p, i, all) => all.findIndex((x) => x.id === p.id) === i)
    .slice(0, 8);
  return {
    solution,
    counts,
    products,
    services: solution.services.map((x) => services.find((s) => s.slug === x)).filter((x): x is ServiceContent => !!x),
    articles: solution.articles.map((x) => articles.find((a) => a.slug === x)).filter((x): x is Article => !!x),
    preview: found.preview,
  };
}
