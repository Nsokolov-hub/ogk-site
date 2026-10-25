// Exports the storefront's texts (src/data/mock, src/data/seo-landings.ts) to backend/seed/content.json once, so the
// backend loads them into PostgreSQL and the admin panel edits them (ADM-02, ADM-07, ADM-10).
// Run: node scripts/export-content-seed.mjs; load: python -m app.catalog.cli seed --content-only
import { writeFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { createJiti } from 'jiti';

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const jiti = createJiti(import.meta.url, { alias: { '@': resolve(root, 'src') } });
const load = (path) => jiti.import(resolve(root, 'src/data', path));

const { siteSettings, siteSettingsEn } = await load('mock/settings.ts');
const { homeContentRu } = await load('mock/home.ts');
const { homeContentEn } = await load('mock/en/home.ts');
const { services, COUNTRIES } = await load('mock/services.ts');
const { servicesEn, COUNTRIES_EN } = await load('mock/en/services.ts');
const { solutions } = await load('mock/solutions.ts');
const { articles, authors } = await load('mock/articles.ts');
const pagesRu = await load('mock/pages.ts');
const pagesEn = await load('mock/en/pages.ts');
const { landings, landingTextEn } = await load('seo-landings.ts');

const clean = (value) => JSON.parse(JSON.stringify(value));
const localized = (ru, en) => (en && en.hasEn !== false && en !== ru ? { ru: clean(ru), en: clean(en) } : { ru: clean(ru) });

const pages = [];
pages.push({ kind: 'home', slug: 'home', position: 0, content: { ru: clean(homeContentRu), en: clean(homeContentEn) } });
services.forEach((ru, i) => {
  const en = servicesEn.find((s) => s.slug === ru.slug);
  pages.push({ kind: 'service', slug: ru.slug, position: i, content: localized(ru, en?.hasEn ? en : undefined) });
});
solutions.forEach((ru, i) => pages.push({ kind: 'solution', slug: ru.slug, position: i, content: { ru: clean(ru) } }));
articles.forEach((ru, i) => pages.push({ kind: 'article', slug: ru.slug, position: i, content: { ru: clean(ru) } }));
authors.forEach((ru, i) => pages.push({ kind: 'author', slug: ru.slug, position: i, content: { ru: clean(ru) } }));

const trust = [
  ['about', pagesRu.aboutPage, pagesEn.aboutPageEn],
  ['delivery', { ...pagesRu.deliveryPage, countries: COUNTRIES }, { ...pagesEn.deliveryPageEn, countries: COUNTRIES_EN }],
  ['documents', pagesRu.documentsPage, pagesEn.documentsPageEn],
  ['contacts', pagesRu.contactsPage, pagesEn.contactsPageEn],
];
trust.forEach(([slug, ru, en], i) =>
  pages.push({ kind: 'trust', slug, position: i, content: { ru: { slug, intro: '', ...clean(ru) }, en: { slug, intro: '', ...clean(en) } } }),
);

const landingRows = landings.map((l, i) => {
  const { parent, slug, preset, ...text } = l;
  const en = landingTextEn[slug];
  return {
    categoryPath: parent,
    slug,
    position: i,
    filters: clean(preset),
    content: en ? { ru: clean(text), en: { ...clean(text), ...clean(en), hasEn: true } } : { ru: clean(text) },
  };
});

const out = {
  note: 'Тексты сайта из src/data/mock на момент переноса в базу; дальше их ведут в админке. Загрузка: python -m app.catalog.cli seed --content-only',
  site: { ru: clean(siteSettings), en: clean(siteSettingsEn) },
  pages,
  landings: landingRows,
};
writeFileSync(resolve(root, 'backend/seed/content.json'), JSON.stringify(out, null, 1) + '\n');
console.log(`backend/seed/content.json: ${pages.length} страниц, ${landingRows.length} посадочных`);
