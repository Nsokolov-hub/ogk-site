// Exports the storefront's test catalog (src/data/mock) to backend/seed/catalog.json once, so the backend can
// load it into PostgreSQL (`python -m app.catalog.cli seed`). Run: node scripts/export-catalog-seed.mjs
import { writeFileSync, mkdirSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { createJiti } from 'jiti';

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const jiti = createJiti(import.meta.url, { alias: { '@': resolve(root, 'src') } });
const load = (path) => jiti.import(resolve(root, 'src/data/mock', path));

const { allCatalogProducts } = await load('catalog-products.ts');
const { mockProducts } = await load('products.ts');
const { productEnrichment } = await load('product-details.ts');
const { productEnrichmentEn, substanceTextEn, DOCUMENT_TITLES_EN } = await load('en/product-details.ts');
const { substances } = await load('substances.ts');
const { brandContent } = await load('brand-content.ts');
const { brandContentEn, brandsWithEn } = await load('en/brand-content.ts');
const { categoryContent } = await load('category-content.ts');
const { categoryContentEn } = await load('en/category-content.ts');
const { catalogTree, categoryNamesEn, categoryShortNames } = await load('categories.ts');
const { CONTROLLED_REGISTER } = await load('controlled.ts');

const shortEn = {
  'reference-standards': 'Reference standards', reagents: 'Reagents', chromatography: 'Chromatography',
  'reference-drugs': 'Reference drugs', 'biological-standards': 'Biological standards',
  'laboratory-equipment': 'Equipment', 'laboratory-glassware': 'Glassware', pharmacopeias: 'Pharmacopoeias',
};
const cardTypeOf = (path) =>
  path.startsWith('chromatography') || path.startsWith('laboratory-equipment') ? 'equipment'
    : path.startsWith('reference-standards') || path.startsWith('reagents') || path.startsWith('reference-drugs') ? 'standard'
      : 'other';

const categories = [];
const addCategory = (node, parent, position) => {
  const path = parent ? `${parent}/${node.slug}` : node.slug;
  const content = categoryContent[path];
  categories.push({
    path, parent: parent || null, slug: node.slug, position,
    nameRu: node.name, nameEn: categoryNamesEn[path] ?? null,
    shortRu: categoryShortNames[path] ?? null, shortEn: shortEn[path] ?? null,
    cardType: cardTypeOf(path), facets: content?.facets ?? [],
    content: { ru: content ?? null, en: categoryContentEn[path] ?? null },
  });
  (node.children ?? []).forEach((child, i) => addCategory(child, path, i));
};
catalogTree.forEach((node, i) => addCategory(node, '', i));
const rootContent = { ru: categoryContent[''] ?? null, en: categoryContentEn[''] ?? null };

const brandBySlug = new Map();
for (const ru of brandContent) {
  const en = brandsWithEn.has(ru.slug) ? brandContentEn.find((b) => b.slug === ru.slug) : null;
  brandBySlug.set(ru.slug, {
    slug: ru.slug, name: ru.name, logo: ru.logo ?? null, country: ru.country ?? null,
    customPackaging: !!ru.customPackaging, wave: ru.wave ?? null, pagePublished: true, content: { ru, en },
  });
}
for (const p of allCatalogProducts) {
  if (!brandBySlug.has(p.brand.slug)) {
    brandBySlug.set(p.brand.slug, {
      slug: p.brand.slug, name: p.brand.name, logo: p.brand.logo ?? null, country: null, customPackaging: false,
      wave: null, pagePublished: false, content: {},
    });
  }
}

const products = allCatalogProducts.map((p) => {
  const e = productEnrichment[p.slug] ?? {};
  const en = productEnrichmentEn[p.slug];
  return {
    slug: p.slug, cardType: p.cardType, name: p.name, nameRu: e.nameRu ?? null, brand: p.brand.slug,
    catalogNumber: p.catalogNumber, cas: p.cas ?? null, altCas: e.altCas ?? [], synonyms: e.synonyms ?? [],
    category: p.categorySlug, packagings: p.packagings.map((x) => ({ key: x.id.slice(p.id.length + 1), label: x.label, catalogNumber: x.catalogNumber ?? null })),
    customPackaging: p.customPackaging, image: p.image ?? null, discontinued: !!p.discontinued,
    substance: p.substance ?? null, attributes: Object.fromEntries(Object.entries(p.attributes ?? {}).filter(([k]) => k !== 'brand' && k !== 'pack')),
    popularity: p.popularity ?? 0, controlled: p.controlled ?? null,
    formula: e.formula ?? null, molecularWeight: e.molecularWeight ?? null, iupacName: e.iupacName ?? null,
    purity: e.purity ?? null, storage: e.storage ?? p.attributes?.storage?.[0] ?? null, shipping: e.shipping ?? null,
    dangerousGoods: e.dangerousGoods ?? null,
    texts: {
      ru: { description: e.description ?? [], specs: e.specs ?? null, faq: e.faq ?? null, monograph: e.monograph ?? null },
      en: en ? { description: en.description ?? [], specs: en.specs ?? null, faq: en.faq ?? null, monograph: en.monograph ?? null } : null,
    },
    documents: (e.documents ?? []).map((d, i) => ({ ...d, titleEn: en?.documents?.[i] ?? DOCUMENT_TITLES_EN[d.type] })),
    updatedAt: e.updatedAt ?? null,
  };
});

const out = {
  note: 'Тестовый каталог витрины для разработки и staging. В production не загружается.',
  root: rootContent,
  categories,
  brands: [...brandBySlug.values()],
  substances: substances.map((s) => ({
    slug: s.slug, nameRu: s.nameRu, nameEn: s.nameEn, cas: s.cas ?? null, formula: s.formula ?? null,
    molecularWeight: s.molecularWeight ?? null, synonyms: s.synonyms ?? [],
    content: { ru: { description: s.description ?? [] }, en: substanceTextEn[s.slug] ?? null },
  })),
  products,
  homeProducts: mockProducts.map((p) => p.slug),
  controlled: CONTROLLED_REGISTER,
};
const file = resolve(root, 'backend/seed/catalog.json');
mkdirSync(dirname(file), { recursive: true });
writeFileSync(file, JSON.stringify(out, null, 1) + '\n');
console.log(`${file}: ${categories.length} categories, ${out.brands.length} brands, ${out.substances.length} substances, ${products.length} products`);
