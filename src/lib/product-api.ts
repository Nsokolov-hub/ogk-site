/**
 * Данные карточек товаров и страниц субстанций (только сервер).
 * Сейчас собираются из моков; позже — fetch к /api/v1/public/products/{slug} и /substances/{slug}.
 */
import type { Locale } from '@/i18n/routing';
import type { Category, ProductDetail, ProductPreview, Substance, SubstanceRole } from '@/types/catalog';
import { catalogProducts } from '@/data/mock/catalog-products';
import { localizedTree } from '@/data/mock/categories';
import { DOCUMENT_TITLES_EN, productEnrichmentEn, substanceTextEn } from '@/data/mock/en/product-details';
import { productEnrichment } from '@/data/mock/product-details';
import { substances } from '@/data/mock/substances';
import { localizeProduct } from './pack-label';

/** Порог индексации по полноте (ТЗ 5.6: стартовое значение 70, настраивается в админке) */
export const INDEX_THRESHOLD = 70;
/** Дата выгрузки ассортимента (ТЗ 9.6) — lastmod для карточек без ручных правок */
const IMPORT_DATE = '2026-10-17';

const bySlug = new Map(catalogProducts.map((p) => [p.slug, p]));
const substanceBySlug = new Map(substances.map((s) => [s.slug, s]));

/** Основная категория товара: [раздел, подраздел?] — для хлебных крошек (ТЗ 5.4) */
export function categoryPath(categorySlug: string, locale: string = 'ru'): Category[] {
  const [topSlug, subSlug] = categorySlug.split('/');
  const top = localizedTree(locale).find((c) => c.slug === topSlug);
  if (!top) return [];
  const sub = subSlug ? top.children?.find((c) => c.slug === subSlug) : undefined;
  return sub ? [top, sub] : [top];
}

const ROLE_LABEL: Record<SubstanceRole, string> = {
  api: 'стандартный образец субстанции',
  impurity: 'стандарт примеси',
  metabolite: 'стандарт метаболита',
  labeled: 'меченое соединение',
};
const ROLE_LABEL_EN: Record<SubstanceRole, string> = {
  api: 'API reference standard',
  impurity: 'impurity standard',
  metabolite: 'metabolite standard',
  labeled: 'labelled compound',
};

/** Короткий шаблонный текст для карточек без собственного описания. Такие карточки не индексируются (ТЗ 10.4). */
function templateDescription(p: ProductPreview, substance: Substance | undefined, locale: string): string[] {
  if (locale !== 'ru') {
    const kind = p.substance ? ROLE_LABEL_EN[p.substance.role] : p.cardType === 'equipment' ? 'item' : 'product';
    const ids = [`cat. No. ${p.catalogNumber}`, p.cas ? `CAS ${p.cas}` : null].filter(Boolean).join(', ');
    return [
      `${p.name} — ${p.brand.name} ${kind}${substance ? ` (${substance.nameEn.toLowerCase()})` : ''}, ${ids}.`,
      'Supplied to order from the manufacturer’s catalogue. We will send the price, lead time and accompanying documents in a quotation within 2 business hours.',
    ];
  }
  const kind = p.substance ? ROLE_LABEL[p.substance.role] : p.cardType === 'equipment' ? 'позиция' : 'товар';
  const ids = [`кат. № ${p.catalogNumber}`, p.cas ? `CAS ${p.cas}` : null].filter(Boolean).join(', ');
  const first = `${p.name} — ${kind} ${p.brand.name}${substance ? ` (${substance.nameRu.toLowerCase()})` : ''}, ${ids}.`;
  return [
    first,
    'Поставляем под заказ из каталога производителя. Цену, срок поставки и состав сопроводительных документов пришлём в коммерческом предложении в течение 2 рабочих часов.',
  ];
}

/** Субстанция на языке страницы: название и описание */
export function localizeSubstance(s: Substance, locale: string): Substance & { hasEn: boolean } {
  const en = substanceTextEn[s.slug];
  if (locale === 'ru') return { ...s, hasEn: !!en };
  return {
    ...s,
    name: s.nameEn,
    synonyms: en?.synonyms,
    description: en?.description,
    molecularWeight: s.molecularWeight?.replace(',', '.'),
    hasEn: !!en,
  };
}

/**
 * Полнота карточки 0–100 (ТЗ 5.6): идентификаторы, структура или фото, уникальное описание от 300 знаков,
 * документ, связь с субстанцией или категорией, условия хранения. Веса настраиваются в админке.
 */
function completeness(p: ProductPreview, d: { description?: string[]; documents?: unknown[]; storage?: string }) {
  let score = 0;
  if (p.name && p.brand && p.catalogNumber && p.categorySlug && (p.packagings.length || p.customPackaging)) score += 20;
  if (p.image) score += 15;
  if ((d.description ?? []).join(' ').length >= 300) score += 25;
  if (d.documents?.length) score += 15;
  if (p.substance || p.categorySlug) score += 10;
  // Условия хранения не применимы к подпискам и изданиям
  if (d.storage || p.categorySlug.startsWith('pharmacopeias')) score += 15;
  return score;
}

export function getProductDetail(slug: string, locale: string = 'ru'): ProductDetail | null {
  const base = bySlug.get(slug);
  if (!base) return null;
  const e = productEnrichment[slug] ?? {};
  const en = productEnrichmentEn[slug];
  const substance = base.substance ? substanceBySlug.get(base.substance.slug) : undefined;
  const isApi = base.substance?.role === 'api';
  const storage = e.storage ?? (base.attributes?.storage?.[0] as ProductDetail['storage'] | undefined);
  const unique = !!e.description?.length;
  const score = completeness(base, { description: e.description, documents: e.documents, storage });
  // Английская версия есть, если описание шаблонное (собирается на любом языке) или переведено (EN-05)
  const hasEn = !unique || !!en;
  const ru = locale === 'ru';

  const detail: ProductDetail = {
    ...base,
    ...e,
    // Формула и масса API — из справочника субстанций, если в карточке их нет
    formula: e.formula ?? (isApi ? substance?.formula : undefined),
    molecularWeight: e.molecularWeight ?? (isApi ? substance?.molecularWeight : undefined),
    storage,
    description: unique ? e.description! : templateDescription(base, substance, 'ru'),
    uniqueDescription: unique,
    documents: e.documents ?? [],
    completeness: score,
    // Ручное переопределение индексации в админке — поле is_indexed (SEO-07)
    indexable: score >= INDEX_THRESHOLD && !base.discontinued,
    hasEn,
    updatedAt: e.updatedAt ?? IMPORT_DATE,
  };
  if (ru) return detail;

  // EN: только переведённые поля; русские тексты без перевода не выводим
  return localizeProduct(
    {
      ...detail,
      description: unique && en ? en.description : templateDescription(base, substance, locale),
      nameRu: undefined,
      molecularWeight: detail.molecularWeight?.replace(',', '.'),
      monograph: en?.monograph,
      specs: en?.specs ?? (e.specs ? [] : undefined),
      documents: detail.documents.map((d, i) => ({ ...d, title: en?.documents?.[i] ?? DOCUMENT_TITLES_EN[d.type] })),
      faq: en?.faq,
    },
    locale,
  );
}

/** Порядок ролей в блоках субстанции: сначала стандарты API, затем примеси, метаболиты, меченые */
const ROLE_ORDER: SubstanceRole[] = ['api', 'impurity', 'metabolite', 'labeled'];
const byRoleThenPopularity = (a: ProductPreview, b: ProductPreview) =>
  ROLE_ORDER.indexOf(a.substance!.role) - ROLE_ORDER.indexOf(b.substance!.role) || (b.popularity ?? 0) - (a.popularity ?? 0);

export interface ProductPageData {
  product: ProductDetail;
  categories: Category[];
  substance?: Substance;
  /** Другие позиции той же субстанции: стандарты, примеси, метаболиты (ТЗ 5.4) */
  sameSubstance: ProductPreview[];
  sameSubstanceTotal: number;
  /** Аналоги других брендов: тот же CAS или те же параметры колонки */
  analogues: ProductPreview[];
  /** Совместимые аксессуары: предколонки к колонке, фильтры */
  accessories: ProductPreview[];
}

const columnKey = (p: ProductPreview) => {
  const a = p.attributes ?? {};
  return [a.phase?.[0], a.length?.[0], a.diameter?.[0], a.particle?.[0]].join('|');
};

export async function getProductPage(slug: string, locale: Locale): Promise<ProductPageData | null> {
  const product = getProductDetail(slug, locale);
  if (!product) return null;
  const rawSubstance = product.substance ? substanceBySlug.get(product.substance.slug) : undefined;
  const substance = rawSubstance ? localizeSubstance(rawSubstance, locale) : undefined;

  const sameSubstanceAll = substance
    ? catalogProducts.filter((p) => p.substance?.slug === substance.slug && p.id !== product.id).sort(byRoleThenPopularity)
    : [];

  let analogues: ProductPreview[] = [];
  if (product.cas) {
    analogues = catalogProducts.filter((p) => p.cas === product.cas && p.brand.slug !== product.brand.slug && p.id !== product.id);
  } else if (product.categorySlug === 'chromatography/hplc-columns') {
    const key = columnKey(product);
    analogues = catalogProducts.filter(
      (p) => p.categorySlug === product.categorySlug && p.brand.slug !== product.brand.slug && columnKey(p) === key,
    );
    // Нет точного совпадения — колонки той же фазы и длины других брендов
    if (!analogues.length) {
      const phase = product.attributes?.phase?.[0];
      const length = product.attributes?.length?.[0];
      analogues = catalogProducts.filter(
        (p) =>
          p.categorySlug === product.categorySlug &&
          p.brand.slug !== product.brand.slug &&
          p.attributes?.phase?.[0] === phase &&
          p.attributes?.length?.[0] === length,
      );
    }
  }
  analogues = analogues.sort((a, b) => (b.popularity ?? 0) - (a.popularity ?? 0)).slice(0, 4);

  let accessories: ProductPreview[] = [];
  if (product.categorySlug === 'chromatography/hplc-columns') {
    const phase = product.attributes?.phase?.[0];
    const guards = catalogProducts
      .filter((p) => p.categorySlug === 'chromatography/precolumns' && p.attributes?.phase?.[0] === phase)
      .sort((a, b) => Number(b.brand.slug === product.brand.slug) - Number(a.brand.slug === product.brand.slug));
    const filters = catalogProducts.filter((p) => p.categorySlug === 'chromatography/filters').slice(0, 1);
    accessories = [...guards.slice(0, 3), ...filters];
  }

  const loc = (list: ProductPreview[]) => list.map((x) => localizeProduct(x, locale));
  return {
    product,
    categories: categoryPath(product.categorySlug, locale),
    substance,
    sameSubstance: loc(sameSubstanceAll.slice(0, 8)),
    sameSubstanceTotal: sameSubstanceAll.length,
    analogues: loc(analogues),
    accessories: loc(accessories),
  };
}

/** Индексируемые карточки для Sitemap (SEO-04, SEO-07): только канонические URL с index */
export function getIndexableProducts(): { slug: string; updatedAt: string; hasEn: boolean }[] {
  return catalogProducts
    .map((p) => getProductDetail(p.slug)!)
    .filter((p) => p.indexable)
    .map((p) => ({ slug: p.slug, updatedAt: p.updatedAt, hasEn: p.hasEn }));
}

// ── субстанции ──

export interface SubstancePageData {
  substance: Substance & { hasEn: boolean };
  items: ProductPreview[];
  groups: { role: SubstanceRole; items: ProductPreview[] }[];
  brands: string[];
  /** index при ≥ 3 позициях и тексте (ТЗ 4.1) */
  indexable: boolean;
}

export async function getSubstancePage(slug: string, locale: string = 'ru'): Promise<SubstancePageData | null> {
  const raw = substanceBySlug.get(slug);
  if (!raw) return null;
  const substance = localizeSubstance(raw, locale);
  const items = catalogProducts
    .filter((p) => p.substance?.slug === slug)
    .sort(byRoleThenPopularity)
    .map((p) => localizeProduct(p, locale));
  if (!items.length) return null;
  const groups = ROLE_ORDER.map((role) => ({ role, items: items.filter((p) => p.substance!.role === role) })).filter(
    (g) => g.items.length,
  );
  const brands = Array.from(new Set(items.map((p) => p.brand.name)));
  return { substance, items, groups, brands, indexable: items.length >= 3 && !!substance.description?.length };
}

export function getSubstanceList(locale: string = 'ru'): (Substance & { count: number; indexable: boolean; hasEn: boolean })[] {
  return substances
    .map((raw) => {
      const s = localizeSubstance(raw, locale);
      const count = catalogProducts.filter((p) => p.substance?.slug === s.slug).length;
      return { ...s, count, indexable: count >= 3 && !!s.description?.length };
    })
    .filter((s) => s.count > 0);
}

/** Превью без полей карточки — для клиентских кнопок «В корзину» и «в 1 клик» */
export function toPreview(p: ProductDetail): ProductPreview {
  return {
    id: p.id,
    slug: p.slug,
    cardType: p.cardType,
    name: p.name,
    brand: p.brand,
    catalogNumber: p.catalogNumber,
    cas: p.cas,
    categorySlug: p.categorySlug,
    packagings: p.packagings,
    customPackaging: p.customPackaging,
    image: p.image,
    discontinued: p.discontinued,
    substance: p.substance,
  };
}
