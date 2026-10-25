/**
 * Карточки товаров и страницы субстанций из API сайта (/api/v1/public/products/{slug}, /substances/*).
 * Только сервер. Шаблонный текст для карточек без описания и английская версия собираются здесь (EN-05).
 */
import type { Locale } from '@/i18n/routing';
import type { Category, DocumentType, ProductDetail, ProductDocument, ProductPreview, SpecRow, Substance, SubstanceRole } from '@/types/catalog';
import type { Faq } from '@/types/content';
import { api, apiOrNull } from './backend';

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

/** Подписи документов по типу — когда у документа нет своего английского названия */
const DOCUMENT_TITLES_EN: Record<DocumentType, string> = {
  coa: 'Certificate of analysis (CoA)',
  sds: 'Safety data sheet (SDS)',
  spec: 'Specification',
  datasheet: 'Datasheet',
  manual: 'Instructions for use',
  certificate: 'Manufacturer certificate',
  'strain-passport': 'Strain product sheet',
  leaflet: 'Leaflet',
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

// ── ответы API ──

interface Texts {
  description?: string[];
  specs?: SpecRow[];
  faq?: Faq[];
  monograph?: string;
}

interface ApiSubstance {
  slug: string;
  nameRu: string;
  nameEn: string;
  cas?: string | null;
  formula?: string | null;
  molecularWeight?: string | null;
  synonyms: string[];
  content: { ru?: { description?: string[] }; en?: { description?: string[]; synonyms?: string[] } };
}

interface ApiProductDetail extends ProductPreview {
  nameRu?: string | null;
  synonyms: string[];
  altCas: string[];
  formula?: string | null;
  molecularWeight?: string | null;
  iupacName?: string | null;
  purity?: string | null;
  storage?: ProductDetail['storage'] | null;
  shipping?: ProductDetail['shipping'] | null;
  dangerousGoods?: boolean | null;
  texts: { ru?: Texts; en?: Texts };
  uniqueDescription: boolean;
  documents: { type: DocumentType; lang: 'ru' | 'en'; titleRu?: string | null; titleEn?: string | null; href?: string | null }[];
  completeness: number;
  indexable: boolean;
  updatedAt: string;
}

interface ApiProductPage {
  moved?: string | null;
  product?: ApiProductDetail | null;
  categories: Category[];
  substance?: ApiSubstance | null;
  sameSubstance: ProductPreview[];
  sameSubstanceTotal: number;
  analogues: ProductPreview[];
  accessories: ProductPreview[];
}

const undef = <T,>(v: T | null | undefined): T | undefined => (v === null ? undefined : v);

/** Субстанция на языке страницы: название и описание */
export function localizeSubstance(s: ApiSubstance, locale: string): Substance & { hasEn: boolean } {
  const en = s.content?.en;
  const base: Substance = {
    slug: s.slug,
    name: s.nameRu,
    nameRu: s.nameRu,
    nameEn: s.nameEn,
    cas: undef(s.cas),
    formula: undef(s.formula),
    molecularWeight: undef(s.molecularWeight),
    synonyms: s.synonyms?.length ? s.synonyms : undefined,
    description: s.content?.ru?.description?.length ? s.content.ru.description : undefined,
  };
  if (locale === 'ru') return { ...base, hasEn: !!en };
  return {
    ...base,
    name: s.nameEn,
    synonyms: en?.synonyms,
    description: en?.description,
    molecularWeight: base.molecularWeight?.replace(',', '.'),
    hasEn: !!en,
  };
}

function toDetail(p: ApiProductDetail, substance: ApiSubstance | null | undefined, locale: string): ProductDetail {
  const ru = locale === 'ru';
  const textRu = p.texts.ru ?? {};
  const textEn = p.texts.en;
  const unique = p.uniqueDescription && !!textRu.description?.length;
  const isApi = p.substance?.role === 'api';
  const sub = substance ? localizeSubstance(substance, 'ru') : undefined;
  // Английская версия есть, если описание шаблонное (собирается на любом языке) или переведено (EN-05)
  const hasEn = !unique || !!textEn;
  const text = ru ? textRu : textEn;
  const documents: ProductDocument[] = p.documents.map((d) => ({
    type: d.type,
    lang: d.lang,
    title: ru ? (d.titleRu ?? DOCUMENT_TITLES_EN[d.type]) : (d.titleEn ?? DOCUMENT_TITLES_EN[d.type]),
    href: undef(d.href),
  }));
  const formula = undef(p.formula) ?? (isApi ? sub?.formula : undefined);
  const molecularWeight = undef(p.molecularWeight) ?? (isApi ? sub?.molecularWeight : undefined);
  return {
    ...p,
    nameRu: ru ? undef(p.nameRu) : undefined,
    synonyms: p.synonyms?.length ? p.synonyms : undefined,
    altCas: p.altCas?.length ? p.altCas : undefined,
    formula,
    molecularWeight: ru ? molecularWeight : molecularWeight?.replace(',', '.'),
    iupacName: undef(p.iupacName),
    purity: undef(p.purity),
    monograph: text?.monograph,
    storage: undef(p.storage),
    shipping: undef(p.shipping),
    dangerousGoods: undef(p.dangerousGoods),
    // У переведённой карточки — свои технические данные; без перевода русские строки не выводим
    specs: ru ? textRu.specs : (textEn?.specs ?? (textRu.specs ? [] : undefined)),
    description: unique && text?.description?.length ? text.description : templateDescription(p, sub, locale),
    uniqueDescription: unique,
    documents,
    faq: text?.faq,
    completeness: p.completeness,
    indexable: p.indexable && !p.discontinued,
    hasEn,
    updatedAt: p.updatedAt,
  };
}

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

/** null — товара нет; { moved } — адрес сменился, страница отвечает 301 (URL-03) */
export async function getProductPage(slug: string, locale: Locale): Promise<ProductPageData | { moved: string } | null> {
  const data = await apiOrNull<ApiProductPage>(`/public/products/${encodeURIComponent(slug)}`, { lang: locale }, { tags: [`product:${slug}`] });
  if (!data) return null;
  if (data.moved) return { moved: data.moved };
  if (!data.product) return null;
  return {
    product: toDetail(data.product, data.substance, locale),
    categories: data.categories,
    substance: data.substance ? localizeSubstance(data.substance, locale) : undefined,
    sameSubstance: data.sameSubstance,
    sameSubstanceTotal: data.sameSubstanceTotal,
    analogues: data.analogues,
    accessories: data.accessories,
  };
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

const ROLE_ORDER: SubstanceRole[] = ['api', 'impurity', 'metabolite', 'labeled'];

export async function getSubstancePage(slug: string, locale: string = 'ru'): Promise<SubstancePageData | { moved: string } | null> {
  const data = await apiOrNull<{ moved?: string | null; substance?: ApiSubstance | null; items: ProductPreview[] }>(
    `/public/substances/${encodeURIComponent(slug)}`,
    { lang: locale },
    { tags: [`substance:${slug}`] },
  );
  if (!data) return null;
  if (data.moved) return { moved: data.moved };
  if (!data.substance || !data.items.length) return null;
  const substance = localizeSubstance(data.substance, locale);
  const groups = ROLE_ORDER.map((role) => ({ role, items: data.items.filter((p) => p.substance?.role === role) })).filter((g) => g.items.length);
  const brands = Array.from(new Set(data.items.map((p) => p.brand.name)));
  return { substance, items: data.items, groups, brands, indexable: data.items.length >= 3 && !!substance.description?.length };
}

export async function getSubstanceList(locale: string = 'ru'): Promise<(Substance & { count: number; indexable: boolean; hasEn: boolean })[]> {
  const rows = await api<(ApiSubstance & { count: number })[]>('/public/substances', undefined, { tags: ['catalog'] });
  return rows.map((row) => {
    const s = localizeSubstance(row, locale);
    return { ...s, count: row.count, indexable: row.count >= 3 && !!s.description?.length };
  });
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
