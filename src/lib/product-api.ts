/**
 * Данные карточек товаров и страниц субстанций (только сервер).
 * Сейчас собираются из моков; позже — fetch к /api/v1/public/products/{slug} и /substances/{slug}.
 */
import type { Locale } from '@/i18n/routing';
import type { Category, ProductDetail, ProductPreview, Substance, SubstanceRole } from '@/types/catalog';
import { catalogProducts } from '@/data/mock/catalog-products';
import { catalogTree } from '@/data/mock/categories';
import { productEnrichment } from '@/data/mock/product-details';
import { substances } from '@/data/mock/substances';

/** Порог индексации по полноте (ТЗ 5.6: стартовое значение 70, настраивается в админке) */
export const INDEX_THRESHOLD = 70;
/** Дата выгрузки ассортимента (ТЗ 9.6) — lastmod для карточек без ручных правок */
const IMPORT_DATE = '2026-10-17';

const bySlug = new Map(catalogProducts.map((p) => [p.slug, p]));
const substanceBySlug = new Map(substances.map((s) => [s.slug, s]));

/** Основная категория товара: [раздел, подраздел?] — для хлебных крошек (ТЗ 5.4) */
export function categoryPath(categorySlug: string): Category[] {
  const [topSlug, subSlug] = categorySlug.split('/');
  const top = catalogTree.find((c) => c.slug === topSlug);
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

/** Короткий шаблонный текст для карточек без собственного описания. Такие карточки не индексируются (ТЗ 10.4). */
function templateDescription(p: ProductPreview, substance?: Substance): string[] {
  const kind = p.substance ? ROLE_LABEL[p.substance.role] : p.cardType === 'equipment' ? 'позиция' : 'товар';
  const ids = [`кат. № ${p.catalogNumber}`, p.cas ? `CAS ${p.cas}` : null].filter(Boolean).join(', ');
  const first = `${p.name} — ${kind} ${p.brand.name}${substance ? ` (${substance.nameRu.toLowerCase()})` : ''}, ${ids}.`;
  return [
    first,
    'Поставляем под заказ из каталога производителя. Цену, срок поставки и состав сопроводительных документов пришлём в коммерческом предложении в течение 2 рабочих часов.',
  ];
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

export function getProductDetail(slug: string): ProductDetail | null {
  const base = bySlug.get(slug);
  if (!base) return null;
  const e = productEnrichment[slug] ?? {};
  const substance = base.substance ? substanceBySlug.get(base.substance.slug) : undefined;
  const isApi = base.substance?.role === 'api';
  const storage = e.storage ?? (base.attributes?.storage?.[0] as ProductDetail['storage'] | undefined);
  const unique = !!e.description?.length;
  const score = completeness(base, { description: e.description, documents: e.documents, storage });

  return {
    ...base,
    ...e,
    // Формула и масса API — из справочника субстанций, если в карточке их нет
    formula: e.formula ?? (isApi ? substance?.formula : undefined),
    molecularWeight: e.molecularWeight ?? (isApi ? substance?.molecularWeight : undefined),
    storage,
    description: unique ? e.description! : templateDescription(base, substance),
    uniqueDescription: unique,
    documents: e.documents ?? [],
    completeness: score,
    // Ручное переопределение индексации в админке — поле is_indexed (SEO-07)
    indexable: score >= INDEX_THRESHOLD && !base.discontinued,
    updatedAt: e.updatedAt ?? IMPORT_DATE,
  };
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
  void locale; // EN-контент карточек — вместе с переводами (EN-04)
  const product = getProductDetail(slug);
  if (!product) return null;
  const substance = product.substance ? substanceBySlug.get(product.substance.slug) : undefined;

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

  return {
    product,
    categories: categoryPath(product.categorySlug),
    substance,
    sameSubstance: sameSubstanceAll.slice(0, 8),
    sameSubstanceTotal: sameSubstanceAll.length,
    analogues,
    accessories,
  };
}

/** Индексируемые карточки для Sitemap (SEO-04, SEO-07): только канонические URL с index */
export function getIndexableProducts(): { slug: string; updatedAt: string }[] {
  return catalogProducts
    .map((p) => getProductDetail(p.slug)!)
    .filter((p) => p.indexable)
    .map((p) => ({ slug: p.slug, updatedAt: p.updatedAt }));
}

// ── субстанции ──

export interface SubstancePageData {
  substance: Substance;
  items: ProductPreview[];
  groups: { role: SubstanceRole; items: ProductPreview[] }[];
  brands: string[];
  /** index при ≥ 3 позициях и тексте (ТЗ 4.1) */
  indexable: boolean;
}

export async function getSubstancePage(slug: string): Promise<SubstancePageData | null> {
  const substance = substanceBySlug.get(slug);
  if (!substance) return null;
  const items = catalogProducts.filter((p) => p.substance?.slug === slug).sort(byRoleThenPopularity);
  if (!items.length) return null;
  const groups = ROLE_ORDER.map((role) => ({ role, items: items.filter((p) => p.substance!.role === role) })).filter(
    (g) => g.items.length,
  );
  const brands = Array.from(new Set(items.map((p) => p.brand.name)));
  return { substance, items, groups, brands, indexable: items.length >= 3 && !!substance.description?.length };
}

export function getSubstanceList(): (Substance & { count: number; indexable: boolean })[] {
  return substances
    .map((s) => {
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
