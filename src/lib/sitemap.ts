/**
 * Sitemap (ТЗ SEO-04, EN-02): индекс /sitemap.xml и файлы по типам страниц — pages, catalog, products (по 25 000 URL),
 * substances, brands, services, solutions, articles. Только канонические URL с ответом 200 и index, с lastmod.
 * Английские файлы (en-*) — только для страниц с переводом (EN-05): главная, каталог, бренды, услуги,
 * страницы доверия, субстанции и карточки с английским текстом.
 */
import { articles, authors } from '@/data/mock/articles';
import { brandContent } from '@/data/mock/brand-content';
import { categoryContent } from '@/data/mock/category-content';
import { categoryContentEn, landingTextEn } from '@/data/mock/en/category-content';
import { landingHref, landings } from '@/data/mock/landings';
import { aboutPage, contactsPage, deliveryPage, documentsPage } from '@/data/mock/pages';
import { services } from '@/data/mock/services';
import { solutions } from '@/data/mock/solutions';
import { isLandingIndexable } from './category-page';
import { brandsFor, servicesFor } from './content-api';
import { getIndexableProducts, getSubstanceList } from './product-api';
import { absoluteUrl, SITE_URL } from './seo';

export const PRODUCTS_PER_FILE = 25_000;
/** Дата последней правки разделов каталога — в проде из админки */
const CATALOG_UPDATED = '2026-10-20';
const HOME_UPDATED = '2026-10-21';

interface Entry {
  path: string;
  lastmod: string;
  hasEn?: boolean;
}

const max = (dates: string[]) => dates.reduce((a, b) => (a > b ? a : b), '1970-01-01');

function sections(): Record<string, Entry[]> {
  const products = getIndexableProducts();
  const substances = getSubstanceList().filter((s) => s.indexable);
  const indexableAuthors = authors.filter((a) => a.bio?.length);

  const out: Record<string, Entry[]> = {
    pages: [
      { path: '/', lastmod: HOME_UPDATED, hasEn: true },
      { path: '/about/', lastmod: aboutPage.updatedAt, hasEn: aboutPage.hasEn },
      { path: '/delivery/', lastmod: deliveryPage.updatedAt, hasEn: deliveryPage.hasEn },
      { path: '/documents/', lastmod: documentsPage.updatedAt, hasEn: documentsPage.hasEn },
      { path: '/contacts/', lastmod: contactsPage.updatedAt, hasEn: contactsPage.hasEn },
      { path: '/brands/', lastmod: max(brandContent.map((b) => b.updatedAt)), hasEn: true },
      { path: '/services/', lastmod: max(services.map((s) => s.updatedAt)), hasEn: true },
      { path: '/solutions/', lastmod: max(solutions.map((s) => s.updatedAt)) },
      { path: '/articles/', lastmod: max(articles.map((a) => a.updatedAt)) },
      { path: '/substances/', lastmod: CATALOG_UPDATED, hasEn: true },
      ...indexableAuthors.map((a) => ({ path: `/authors/${a.slug}/`, lastmod: max(articles.filter((x) => x.authorSlug === a.slug).map((x) => x.updatedAt)) })),
    ],
    catalog: [
      ...Object.keys(categoryContent).map((key) => ({
        path: key ? `/catalog/${key}/` : '/catalog/',
        lastmod: CATALOG_UPDATED,
        hasEn: !!categoryContentEn[key],
      })),
      // SEO-посадочные из срезов (URL-07) — только с достаточным числом позиций
      ...landings
        .filter(isLandingIndexable)
        .map((l) => ({ path: landingHref(l), lastmod: l.updatedAt, hasEn: !!categoryContentEn[l.parent] && !!landingTextEn[l.slug] })),
    ],
    substances: substances.map((s) => ({ path: `/substances/${s.slug}/`, lastmod: CATALOG_UPDATED, hasEn: s.hasEn })),
    brands: brandsFor('ru').map((b) => ({ path: `/brands/${b.slug}/`, lastmod: b.updatedAt, hasEn: b.hasEn })),
    services: servicesFor('ru').map((s) => ({ path: `/services/${s.slug}/`, lastmod: s.updatedAt, hasEn: s.hasEn })),
    solutions: solutions.map((s) => ({ path: `/solutions/${s.slug}/`, lastmod: s.updatedAt, hasEn: s.hasEn })),
    articles: articles.map((a) => ({ path: `/articles/${a.slug}/`, lastmod: a.updatedAt, hasEn: a.hasEn })),
  };
  for (let i = 0; i * PRODUCTS_PER_FILE < products.length; i++) {
    out[`products-${i + 1}`] = products
      .slice(i * PRODUCTS_PER_FILE, (i + 1) * PRODUCTS_PER_FILE)
      .map((p) => ({ path: `/product/${p.slug}/`, lastmod: p.updatedAt, hasEn: p.hasEn }));
  }
  return out;
}

/** Все файлы: ru — как есть, en-* — только переведённые страницы */
export function sitemapFiles(): Record<string, { loc: string; lastmod: string }[]> {
  const files: Record<string, { loc: string; lastmod: string }[]> = {};
  for (const [name, entries] of Object.entries(sections())) {
    files[name] = entries.map((e) => ({ loc: absoluteUrl('ru', e.path), lastmod: e.lastmod }));
    const en = entries.filter((e) => e.hasEn).map((e) => ({ loc: absoluteUrl('en', e.path), lastmod: e.lastmod }));
    if (en.length) files[`en-${name}`] = en;
  }
  for (const k of Object.keys(files)) if (!files[k].length) delete files[k];
  return files;
}

const esc = (s: string) => s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');

export function sitemapIndexXml(): string {
  const files = sitemapFiles();
  const items = Object.entries(files)
    .map(([name, urls]) => `  <sitemap>\n    <loc>${SITE_URL}/sitemaps/${name}.xml</loc>\n    <lastmod>${max(urls.map((u) => u.lastmod))}</lastmod>\n  </sitemap>`)
    .join('\n');
  return `<?xml version="1.0" encoding="UTF-8"?>\n<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n${items}\n</sitemapindex>\n`;
}

export function sitemapFileXml(name: string): string | null {
  const urls = sitemapFiles()[name];
  if (!urls) return null;
  const items = urls.map((u) => `  <url>\n    <loc>${esc(u.loc)}</loc>\n    <lastmod>${u.lastmod}</lastmod>\n  </url>`).join('\n');
  return `<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n${items}\n</urlset>\n`;
}
