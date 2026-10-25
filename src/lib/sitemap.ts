/**
 * Sitemap (ТЗ SEO-04, EN-02): индекс /sitemap.xml и файлы по типам страниц — pages, catalog, products (по 25 000 URL),
 * substances, brands, services, solutions, articles. Только канонические URL с ответом 200 и index, с lastmod.
 * Английские файлы (en-*) — только для страниц с переводом (EN-05): главная, каталог, бренды, услуги,
 * страницы доверия, субстанции и карточки с английским текстом.
 */
import { articles, authors } from '@/data/mock/articles';
import { aboutPage, contactsPage, deliveryPage, documentsPage } from '@/data/mock/pages';
import { services } from '@/data/mock/services';
import { solutions } from '@/data/mock/solutions';
import { landingHref, landings, landingTextEn } from '@/data/seo-landings';
import type { Schemas } from './api-types';
import { api } from './backend';
import { isLandingIndexable } from './category-page';
import { brandsFor, servicesFor } from './content-api';
import { getSubstanceList } from './product-api';
import { absoluteUrl, SITE_URL } from './seo';

/** Карточек в одном файле: столько отдаёт API за страницу (SEO-04) */
export const PRODUCTS_PER_FILE = 25_000;
const HOME_UPDATED = '2026-10-21';

type ApiCategoryEntry = Schemas['CategoryNode'];
type ProductsPage = Schemas['SitemapPage'];

const productsPage = (page: number) => api<ProductsPage>('/public/catalog/sitemap', { page }, { revalidate: 3600, tags: ['catalog'] });

interface Entry {
  path: string;
  lastmod: string;
  hasEn?: boolean;
}

const max = (dates: string[]) => dates.reduce((a, b) => (a > b ? a : b), '1970-01-01');

/** Все разделы, кроме карточек товаров: карточки идут отдельными файлами products-N */
async function sections(): Promise<Record<string, Entry[]>> {
  const [tree, root, substancesAll, brands] = await Promise.all([
    api<ApiCategoryEntry[]>('/public/catalog/tree', undefined, { revalidate: 3600, tags: ['catalog'] }),
    api<Schemas['CategoryOut']>('/public/catalog/category', { path: '' }, { revalidate: 3600, tags: ['catalog'] }),
    getSubstanceList(),
    brandsFor('ru'),
  ]);
  const categories = tree.flatMap((c) => [c, ...(c.children ?? [])]);
  const catalogUpdated = max(categories.map((c) => c.updatedAt ?? '').filter(Boolean));
  const substances = substancesAll.filter((s) => s.indexable);
  const indexableAuthors = authors.filter((a) => a.bio?.length);
  const landingFlags = await Promise.all(landings.map(isLandingIndexable));
  const hasEn = new Map(categories.map((c) => [c.path, !!c.hasEn]));

  return {
    pages: [
      { path: '/', lastmod: HOME_UPDATED, hasEn: true },
      { path: '/about/', lastmod: aboutPage.updatedAt, hasEn: aboutPage.hasEn },
      { path: '/delivery/', lastmod: deliveryPage.updatedAt, hasEn: deliveryPage.hasEn },
      { path: '/documents/', lastmod: documentsPage.updatedAt, hasEn: documentsPage.hasEn },
      { path: '/contacts/', lastmod: contactsPage.updatedAt, hasEn: contactsPage.hasEn },
      { path: '/brands/', lastmod: max(brands.map((b) => b.updatedAt)), hasEn: true },
      { path: '/services/', lastmod: max(services.map((s) => s.updatedAt)), hasEn: true },
      { path: '/solutions/', lastmod: max(solutions.map((s) => s.updatedAt)) },
      { path: '/articles/', lastmod: max(articles.map((a) => a.updatedAt)) },
      { path: '/substances/', lastmod: catalogUpdated, hasEn: true },
      ...indexableAuthors.map((a) => ({ path: `/authors/${a.slug}/`, lastmod: max(articles.filter((x) => x.authorSlug === a.slug).map((x) => x.updatedAt)) })),
    ],
    catalog: [
      { path: '/catalog/', lastmod: catalogUpdated, hasEn: !!root.content.en },
      ...categories.map((c) => ({ path: `/catalog/${c.path}/`, lastmod: c.updatedAt || catalogUpdated, hasEn: !!c.hasEn })),
      // SEO-посадочные из срезов (URL-07) — только с достаточным числом позиций
      ...landings
        .filter((_, i) => landingFlags[i])
        .map((l) => ({ path: landingHref(l), lastmod: l.updatedAt, hasEn: !!hasEn.get(l.parent) && !!landingTextEn[l.slug] })),
    ],
    substances: substances.map((s) => ({ path: `/substances/${s.slug}/`, lastmod: catalogUpdated, hasEn: s.hasEn })),
    brands: brands.map((b) => ({ path: `/brands/${b.slug}/`, lastmod: b.updatedAt, hasEn: b.hasEn })),
    services: servicesFor('ru').map((s) => ({ path: `/services/${s.slug}/`, lastmod: s.updatedAt, hasEn: s.hasEn })),
    solutions: solutions.map((s) => ({ path: `/solutions/${s.slug}/`, lastmod: s.updatedAt, hasEn: s.hasEn })),
    articles: articles.map((a) => ({ path: `/articles/${a.slug}/`, lastmod: a.updatedAt, hasEn: a.hasEn })),
  };
}

const productEntries = async (n: number): Promise<Entry[]> =>
  (await productsPage(n)).items.map((p) => ({ path: `/product/${p.slug}/`, lastmod: p.updatedAt, hasEn: p.hasEn }));

/** Файлы карты: ru — как есть, en-* — только переведённые страницы; пустые файлы не выводим */
function files(name: string, entries: Entry[]): Record<string, { loc: string; lastmod: string }[]> {
  const out: Record<string, { loc: string; lastmod: string }[]> = {};
  if (entries.length) out[name] = entries.map((e) => ({ loc: absoluteUrl('ru', e.path), lastmod: e.lastmod }));
  const en = entries.filter((e) => e.hasEn).map((e) => ({ loc: absoluteUrl('en', e.path), lastmod: e.lastmod }));
  if (en.length) out[`en-${name}`] = en;
  return out;
}

export async function sitemapFiles(): Promise<Record<string, { loc: string; lastmod: string }[]>> {
  const all: Record<string, { loc: string; lastmod: string }[]> = {};
  for (const [name, entries] of Object.entries(await sections())) Object.assign(all, files(name, entries));
  const first = await productsPage(1);
  for (let n = 1; n <= first.pageCount && first.total > 0; n += 1) {
    Object.assign(all, files(`products-${n}`, n === 1 ? first.items.map((p) => ({ path: `/product/${p.slug}/`, lastmod: p.updatedAt, hasEn: p.hasEn })) : await productEntries(n)));
  }
  return all;
}

const esc = (s: string) => s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');

export async function sitemapIndexXml(): Promise<string> {
  const all = await sitemapFiles();
  const items = Object.entries(all)
    .map(([name, urls]) => `  <sitemap>\n    <loc>${SITE_URL}/sitemaps/${name}.xml</loc>\n    <lastmod>${max(urls.map((u) => u.lastmod))}</lastmod>\n  </sitemap>`)
    .join('\n');
  return `<?xml version="1.0" encoding="UTF-8"?>\n<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n${items}\n</sitemapindex>\n`;
}

export async function sitemapFileXml(name: string): Promise<string | null> {
  const product = name.match(/^(en-)?products-(\d+)$/);
  const urls = product
    ? files(`products-${product[2]}`, await productEntries(Number(product[2])))[name]
    : (await sitemapFiles())[name];
  if (!urls) return null;
  const items = urls.map((u) => `  <url>\n    <loc>${esc(u.loc)}</loc>\n    <lastmod>${u.lastmod}</lastmod>\n  </url>`).join('\n');
  return `<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n${items}\n</urlset>\n`;
}
