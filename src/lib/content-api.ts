/**
 * Контент страниц из админки (ADM-02): бренды, услуги, статьи, авторы, страницы доверия. Только сервер.
 * Сейчас — моки; позже — fetch к /api/v1/public/pages/*. Сигнатуры не меняем.
 */
import type { Locale } from '@/i18n/routing';
import type { ProductPreview } from '@/types/catalog';
import type { Article, Author, BrandContent, ServiceContent, SolutionContent } from '@/types/content';
import { articles, authors } from '@/data/mock/articles';
import { brandContent } from '@/data/mock/brand-content';
import { brandContentEn, brandsWithEn } from '@/data/mock/en/brand-content';
import { catalogProducts } from '@/data/mock/catalog-products';
import { servicesEn } from '@/data/mock/en/services';
import { services } from '@/data/mock/services';
import { solutions } from '@/data/mock/solutions';
import { localizeProduct } from './pack-label';

const byPopularity = (a: ProductPreview, b: ProductPreview) => (b.popularity ?? 0) - (a.popularity ?? 0);

// ── бренды ──

export interface BrandListItem extends BrandContent {
  count: number;
}

/** Бренды на языке страницы; у русских отмечено, есть ли перевод (для hreflang и Sitemap) */
export function brandsFor(locale: string): BrandContent[] {
  return locale === 'en' ? brandContentEn : brandContent.map((b) => ({ ...b, hasEn: brandsWithEn.has(b.slug) }));
}

export async function getBrands(locale: Locale): Promise<BrandListItem[]> {
  return brandsFor(locale).map((b) => ({ ...b, count: catalogProducts.filter((p) => p.brand.slug === b.slug).length }));
}

export interface BrandPageData {
  brand: BrandContent;
  count: number;
  products: ProductPreview[];
  /** Подкатегории каталога, где представлен бренд, с числом позиций */
  categories: { slug: string; count: number }[];
}

export async function getBrandPage(slug: string, locale: Locale): Promise<BrandPageData | null> {
  const brand = brandsFor(locale).find((b) => b.slug === slug);
  if (!brand) return null;
  const items = catalogProducts.filter((p) => p.brand.slug === slug).sort(byPopularity);
  const categories = new Map<string, number>();
  for (const p of items) categories.set(p.categorySlug, (categories.get(p.categorySlug) ?? 0) + 1);
  return {
    brand,
    count: items.length,
    products: items.slice(0, 8).map((p) => localizeProduct(p, locale)),
    categories: Array.from(categories, ([s, count]) => ({ slug: s, count })).sort((a, b) => b.count - a.count),
  };
}

// ── услуги ──

const servicesWithEn = new Set(servicesEn.filter((s) => s.hasEn).map((s) => s.slug));

/** Услуги на языке страницы; у русских отмечено, есть ли перевод (для hreflang и Sitemap) */
export function servicesFor(locale: string): ServiceContent[] {
  return locale === 'en' ? servicesEn : services.map((s) => ({ ...s, hasEn: servicesWithEn.has(s.slug) }));
}

export async function getServices(locale: Locale): Promise<ServiceContent[]> {
  return servicesFor(locale);
}

export async function getService(slug: string, locale: Locale): Promise<ServiceContent | null> {
  return servicesFor(locale).find((s) => s.slug === slug) ?? null;
}

// ── статьи ──

export async function getArticles(locale: Locale): Promise<Article[]> {
  void locale;
  return [...articles].sort((a, b) => b.publishedAt.localeCompare(a.publishedAt));
}

export async function getArticle(slug: string, locale: Locale): Promise<Article | null> {
  void locale;
  return articles.find((a) => a.slug === slug) ?? null;
}

export async function getAuthor(slug: string): Promise<Author | null> {
  return authors.find((a) => a.slug === slug) ?? null;
}

export function getAuthors(): Author[] {
  return authors;
}

// ── отраслевые решения ──

const inScope = (p: ProductPreview, scope: string[]) => scope.some((c) => p.categorySlug === c || p.categorySlug.startsWith(`${c}/`));

export async function getSolutions(locale: Locale): Promise<SolutionContent[]> {
  void locale;
  return solutions;
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

export async function getSolutionPage(slug: string, locale: Locale): Promise<SolutionPageData | null> {
  const solution = solutions.find((s) => s.slug === slug);
  if (!solution) return null;
  return {
    solution,
    counts: solution.groups.map((g) => catalogProducts.filter((p) => inScope(p, g.scope)).length),
    products: catalogProducts
      .filter((p) => inScope(p, solution.featured))
      .sort(byPopularity)
      .slice(0, 8)
      .map((p) => localizeProduct(p, locale)),
    services: solution.services.map((x) => servicesFor(locale).find((s) => s.slug === x)).filter((x): x is ServiceContent => !!x),
    articles: solution.articles.map((x) => articles.find((a) => a.slug === x)).filter((x): x is Article => !!x),
  };
}
