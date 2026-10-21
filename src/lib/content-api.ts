/**
 * Контент страниц из админки (ADM-02): бренды, услуги, статьи, авторы, страницы доверия. Только сервер.
 * Сейчас — моки; позже — fetch к /api/v1/public/pages/*. Сигнатуры не меняем.
 */
import type { Locale } from '@/i18n/routing';
import type { ProductPreview } from '@/types/catalog';
import type { Article, Author, BrandContent, ServiceContent } from '@/types/content';
import { articles, authors } from '@/data/mock/articles';
import { brandContent } from '@/data/mock/brand-content';
import { catalogProducts } from '@/data/mock/catalog-products';
import { services } from '@/data/mock/services';

const byPopularity = (a: ProductPreview, b: ProductPreview) => (b.popularity ?? 0) - (a.popularity ?? 0);

// ── бренды ──

export interface BrandListItem extends BrandContent {
  count: number;
}

export async function getBrands(locale: Locale): Promise<BrandListItem[]> {
  void locale;
  return brandContent.map((b) => ({ ...b, count: catalogProducts.filter((p) => p.brand.slug === b.slug).length }));
}

export interface BrandPageData {
  brand: BrandContent;
  count: number;
  products: ProductPreview[];
  /** Подкатегории каталога, где представлен бренд, с числом позиций */
  categories: { slug: string; count: number }[];
}

export async function getBrandPage(slug: string, locale: Locale): Promise<BrandPageData | null> {
  void locale;
  const brand = brandContent.find((b) => b.slug === slug);
  if (!brand) return null;
  const items = catalogProducts.filter((p) => p.brand.slug === slug).sort(byPopularity);
  const categories = new Map<string, number>();
  for (const p of items) categories.set(p.categorySlug, (categories.get(p.categorySlug) ?? 0) + 1);
  return {
    brand,
    count: items.length,
    products: items.slice(0, 8),
    categories: Array.from(categories, ([s, count]) => ({ slug: s, count })).sort((a, b) => b.count - a.count),
  };
}

// ── услуги ──

export async function getServices(locale: Locale): Promise<ServiceContent[]> {
  void locale;
  return services;
}

export async function getService(slug: string, locale: Locale): Promise<ServiceContent | null> {
  void locale;
  return services.find((s) => s.slug === slug) ?? null;
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
