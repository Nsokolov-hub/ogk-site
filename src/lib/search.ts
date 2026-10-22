import type { ProductPreview } from '@/types/catalog';
import { brandContent } from '@/data/mock/brand-content';
import { catalogProducts } from '@/data/mock/catalog-products';
import { localizedTree } from '@/data/mock/categories';
import { landingTextEn } from '@/data/mock/en/category-content';
import { landingHref, landings } from '@/data/mock/landings';
import { productEnrichment } from '@/data/mock/product-details';
import { substances } from '@/data/mock/substances';
import { SUGGEST_LIMIT, SUGGEST_MIN, type SuggestItem, type SuggestResult } from './search-shared';

export type { SuggestItem, SuggestResult } from './search-shared';

/**
 * Поиск по каталогу (ТЗ 6). Сейчас считается по мокам на сервере; в проде это Meilisearch за
 * /api/v1/public/search/* — меняются только тела функций, форма ответа остаётся.
 *
 * Порядок (SRCH-04): точный кат. № или CAS → брутто-формула (SRCH-10) → начало кат. № / CAS →
 * название с начала слова → вхождение в название. Русские названия субстанций ищут английские (SRCH-05),
 * запрос в неверной раскладке исправляется, если по исходному ничего не нашлось.
 */

/** Кат. № и CAS сравниваем без пробелов, дефисов и точек: «1.00030» = «100030», «58 08 2» = «58-08-2» */
const compact = (s: string) => s.toLowerCase().replace(/[\s.\-–/]/g, '');
const words = (s: string) => s.toLowerCase().split(/[\s,;()[\]]+/).filter(Boolean);
const normalize = (s: string) => s.trim().toLowerCase().replace(/\s+/g, ' ');

// ── брутто-формула (SRCH-10) ──

/** Двухбуквенные элементы, которые встречаются в фармацевтике; остальные пары читаем как два элемента */
const TWO_LETTER = new Set(['Cl', 'Br', 'Na', 'Ca', 'Mg', 'Li', 'Si', 'Se', 'Zn', 'Fe', 'Al', 'Pt', 'Ag', 'Au']);

/** «C15H12N2O2», «c15h12n2o2», «C15 H12 N2 O2» → ключ в порядке Хилла; не формула → null */
export function hillKey(input: string): string | null {
  const raw = input.replace(/\s+/g, '');
  if (!/^[A-Za-z0-9]+$/.test(raw) || !/\d/.test(raw) || !/[cC]/.test(raw)) return null;
  const mixedCase = /[a-z]/.test(raw) && /[A-Z]/.test(raw);
  const counts = new Map<string, number>();
  let i = 0;
  while (i < raw.length) {
    const up = raw[i].toUpperCase();
    if (!/[A-Z]/.test(up)) return null;
    let el = up;
    const next = raw[i + 1];
    if (next && /[a-zA-Z]/.test(next)) {
      const pair = up + next.toLowerCase();
      // В записи с регистром строчная буква всегда продолжает символ; без регистра — только известные пары
      if (mixedCase ? next === next.toLowerCase() : TWO_LETTER.has(pair)) el = pair;
    }
    i += el.length;
    let n = '';
    while (i < raw.length && /\d/.test(raw[i])) n += raw[i++];
    counts.set(el, (counts.get(el) ?? 0) + (n ? Number(n) : 1));
  }
  if (!counts.has('C')) return null;
  const order = ['C', 'H', ...Array.from(counts.keys()).filter((e) => e !== 'C' && e !== 'H').sort()];
  return order.filter((e) => counts.has(e)).map((e) => `${e}${counts.get(e) === 1 ? '' : counts.get(e)}`).join('');
}

const substanceBySlug = new Map(substances.map((s) => [s.slug, s]));
/** Формула позиции: из карточки, иначе у стандарта субстанции — из справочника субстанций */
const productFormula = (p: ProductPreview) =>
  productEnrichment[p.slug]?.formula ?? (p.substance?.role === 'api' ? substanceBySlug.get(p.substance.slug)?.formula : undefined);
const formulaIndex = new Map<string, string>();
for (const p of catalogProducts) {
  const f = productFormula(p);
  const key = f ? hillKey(f) : null;
  if (key) formulaIndex.set(p.id, key);
}

// ── синонимы RU ↔ EN (SRCH-05) и раскладка ──

/** Русские названия и синонимы субстанций → английское название для поиска по названиям товаров */
const RU_TO_EN = substances.flatMap((s) =>
  [s.nameRu, ...(s.synonyms ?? [])].map((ru) => ({ ru: ru.toLowerCase(), en: s.nameEn.toLowerCase().split(/[\s,]+/)[0] })),
);

function synonymQueries(q: string): string[] {
  if (!/[а-яё]/i.test(q)) return [];
  const hits = RU_TO_EN.filter(({ ru }) => words(ru).some((w) => w.startsWith(q)) || q.startsWith(ru.split(' ')[0]));
  return Array.from(new Set(hits.map((h) => h.en)));
}

const EN = "qwertyuiop[]asdfghjkl;'zxcvbnm,.`";
const RU = 'йцукенгшщзхъфывапролджэячсмитьбюё';
/** «jrcrfh,fptgby» → «окскарбазепин» и обратно */
export function switchLayout(q: string): string {
  const latin = /[a-z]/i.test(q) && !/[а-яё]/i.test(q);
  const [from, to] = latin ? [EN, RU] : [RU, EN];
  return q
    .toLowerCase()
    .split('')
    .map((ch) => {
      const i = from.indexOf(ch);
      return i >= 0 ? to[i] : ch;
    })
    .join('');
}

// ── ранжирование ──

function rank(p: ProductPreview, q: string, qc: string, formula: string | null): [number, SuggestItem['match']] | null {
  const num = compact(p.catalogNumber);
  const cas = p.cas ? compact(p.cas) : '';
  if (qc && (num === qc || cas === qc)) return [0, num === qc ? 'catalogNumber' : 'cas'];
  if (formula && formulaIndex.get(p.id) === formula) return [1, 'formula'];
  if (qc.length >= 3 && num.startsWith(qc)) return [2, 'catalogNumber'];
  if (qc.length >= 3 && cas && cas.startsWith(qc)) return [2, 'cas'];
  const name = p.name.toLowerCase();
  if (words(name).some((w) => w.startsWith(q))) return [name.startsWith(q) ? 3 : 4, 'name'];
  if (name.includes(q)) return [5, 'name'];
  // Запрос по бренду («waters», «edqm») — все позиции бренда, ниже совпадений по названию (SRCH-02)
  if (q.length >= 3 && (p.brand.slug.startsWith(q) || words(p.brand.name).some((w) => w.startsWith(q)))) return [6, 'brand'];
  return null;
}

interface Ranked {
  p: ProductPreview;
  r: number;
  match: SuggestItem['match'];
}

function rankAll(q: string): Ranked[] {
  const formula = hillKey(q);
  const found = new Map<string, Ranked>();
  const run = (query: string, penalty: number) => {
    const qcx = compact(query);
    for (const p of catalogProducts) {
      const res = rank(p, query, qcx, penalty ? null : formula);
      if (!res) continue;
      const prev = found.get(p.id);
      if (!prev || prev.r > res[0] + penalty) found.set(p.id, { p, r: res[0] + penalty, match: res[1] });
    }
  };
  run(q, 0);
  // Русское название субстанции → английские названия товаров (окскарбазепин → Oxcarbazepine CRS)
  for (const alt of synonymQueries(q)) run(alt, 0.5);
  return Array.from(found.values()).sort(
    (a, b) => a.r - b.r || (b.p.popularity ?? 0) - (a.p.popularity ?? 0) || a.p.name.localeCompare(b.p.name, 'en'),
  );
}

/**
 * Товары по запросу. Если ничего не нашлось, пробуем запрос в другой раскладке (SRCH-05):
 * в ответе `corrected` — исправленный запрос, его показываем пользователю.
 */
export function findProducts(query: string): { items: Ranked[]; corrected?: string } {
  const q = normalize(query);
  if (q.length < SUGGEST_MIN) return { items: [] };
  const items = rankAll(q);
  if (items.length) return { items };
  const switched = switchLayout(q);
  if (switched !== q) {
    const alt = rankAll(switched);
    if (alt.length) return { items: alt, corrected: switched };
  }
  return { items: [] };
}

// ── группы подсказок: субстанции, категории, бренды (SRCH-01) ──

const startsWord = (text: string, q: string) => words(text).some((w) => w.startsWith(q)) || text.toLowerCase().startsWith(q);

const categoryEntries = (lang: string) => [
  ...localizedTree(lang).flatMap((c) => [
    { name: c.name, href: c.href },
    ...(c.children ?? []).map((s) => ({ name: `${s.name} — ${c.name}`, href: s.href })),
  ]),
  ...landings.map((l) => ({ name: (lang === 'en' ? landingTextEn[l.slug]?.h1 : undefined) ?? l.h1, href: landingHref(l) })),
];
const CATEGORY_ENTRIES: Record<string, { name: string; href: string }[]> = { ru: categoryEntries('ru'), en: categoryEntries('en') };

export function suggestGroups(q: string, lang = 'ru') {
  const qc = compact(q);
  const subs = substances
    .filter((s) => [s.nameRu, s.nameEn, ...(s.synonyms ?? [])].some((n) => startsWord(n, q)) || (s.cas && compact(s.cas) === qc))
    .slice(0, 3)
    .map((s) => ({ slug: s.slug, name: s.nameRu, nameEn: s.nameEn }));
  const categories = q.length >= 3 ? (CATEGORY_ENTRIES[lang] ?? CATEGORY_ENTRIES.ru).filter((c) => startsWord(c.name, q)).slice(0, 3) : [];
  const brands = brandContent.filter((b) => startsWord(b.name, q) || b.slug.startsWith(q)).slice(0, 3).map((b) => ({ slug: b.slug, name: b.name }));
  return { substances: subs, categories, brands };
}

export function suggest(query: string, limit = SUGGEST_LIMIT, lang = 'ru'): SuggestResult {
  const q = normalize(query);
  if (q.length < SUGGEST_MIN) return { query, items: [], total: 0, substances: [], categories: [], brands: [] };
  const { items: found, corrected } = findProducts(q);
  const groups = suggestGroups(corrected ?? q, lang);

  return {
    query,
    corrected,
    total: found.length,
    ...groups,
    items: found.slice(0, limit).map(({ p, match }) => ({
      id: p.id,
      slug: p.slug,
      name: p.name,
      brand: p.brand.name,
      catalogNumber: p.catalogNumber,
      cas: p.cas,
      formula: match === 'formula' ? productFormula(p) : undefined,
      cardType: p.cardType,
      match,
    })),
  };
}

// ── страница результатов /search/ (SRCH-07) ──

export interface SearchFacetValue {
  value: string;
  label: string;
  count: number;
  selected: boolean;
}

export interface SearchPageResult {
  query: string;
  /** Запрос в исправленной раскладке, если по исходному ничего не нашлось */
  corrected?: string;
  items: ProductPreview[];
  total: number;
  page: number;
  pageCount: number;
  facets: { brand: SearchFacetValue[]; category: SearchFacetValue[] };
}

export const SEARCH_PAGE_SIZE = 24;

/** Полная выдача с фильтрами по бренду и разделу и счётчиками; порядок — как у подсказок (SRCH-04) */
export function searchCatalog(p: {
  query: string;
  brand?: string;
  category?: string;
  page?: number;
  categoryNames: Record<string, string>;
}): SearchPageResult {
  const empty = { query: p.query, items: [], total: 0, page: 1, pageCount: 1, facets: { brand: [], category: [] } };
  if (normalize(p.query).length < SUGGEST_MIN) return empty;
  const { items: found, corrected } = findProducts(p.query);
  const all = found.map((f) => f.p);
  const topOf = (prod: ProductPreview) => prod.categorySlug.split('/')[0];

  // Счётчики фасета считаем с учётом другого фильтра — так видны альтернативы
  const byBrand = all.filter((x) => !p.category || topOf(x) === p.category);
  const byCategory = all.filter((x) => !p.brand || x.brand.slug === p.brand);
  const count = (list: ProductPreview[], key: (x: ProductPreview) => string, label: (x: ProductPreview) => string, selected?: string) => {
    const m = new Map<string, SearchFacetValue>();
    for (const x of list) {
      const k = key(x);
      const v = m.get(k) ?? { value: k, label: label(x), count: 0, selected: k === selected };
      v.count += 1;
      m.set(k, v);
    }
    if (selected && !m.has(selected)) m.set(selected, { value: selected, label: selected, count: 0, selected: true });
    return Array.from(m.values()).sort((a, b) => b.count - a.count || a.label.localeCompare(b.label));
  };

  const filtered = all.filter((x) => (!p.brand || x.brand.slug === p.brand) && (!p.category || topOf(x) === p.category));
  const pageCount = Math.max(1, Math.ceil(filtered.length / SEARCH_PAGE_SIZE));
  const page = Math.min(Math.max(1, p.page ?? 1), pageCount);

  return {
    query: p.query,
    corrected,
    items: filtered.slice((page - 1) * SEARCH_PAGE_SIZE, page * SEARCH_PAGE_SIZE),
    total: filtered.length,
    page,
    pageCount,
    facets: {
      brand: count(byBrand, (x) => x.brand.slug, (x) => x.brand.name, p.brand),
      category: count(byCategory, topOf, (x) => p.categoryNames[topOf(x)] ?? topOf(x), p.category),
    },
  };
}

// ── пакетный поиск по списку (SRCH-09, SC-02) ──

export const BATCH_LIMIT = 200;

export type BatchCandidate = Pick<
  ProductPreview,
  'id' | 'slug' | 'name' | 'brand' | 'catalogNumber' | 'cas' | 'categorySlug' | 'packagings' | 'customPackaging' | 'cardType'
>;

export interface BatchLineResult {
  line: string;
  query: string;
  quantity: number;
  /** exact — найдено точно; multiple — несколько кандидатов, нужен выбор; none — свободная строка */
  status: 'exact' | 'multiple' | 'none';
  candidates: BatchCandidate[];
}

const toCandidate = (x: ProductPreview): BatchCandidate => ({
  id: x.id,
  slug: x.slug,
  name: x.name,
  brand: x.brand,
  catalogNumber: x.catalogNumber,
  cas: x.cas,
  categorySlug: x.categorySlug,
  packagings: x.packagings,
  customPackaging: x.customPackaging,
  cardType: x.cardType,
});

/** «Y0001897 2», «28721-07-5;3», «Paracetamol CRS» → запрос и количество */
export function parseLine(line: string): { query: string; quantity: number } {
  const cols = line.split(/\t|;/).map((c) => c.trim()).filter(Boolean);
  if (cols.length >= 2 && /^\d{1,3}$/.test(cols[cols.length - 1])) {
    return { query: cols.slice(0, -1).join(' '), quantity: Number(cols[cols.length - 1]) };
  }
  const words = line.trim().split(/\s+/);
  if (words.length === 2 && /^\d{1,3}$/.test(words[1]) && /\d/.test(words[0])) {
    return { query: words[0], quantity: Number(words[1]) };
  }
  return { query: line.trim(), quantity: 1 };
}

export function matchLines(lines: string[]): BatchLineResult[] {
  return lines
    .map((l) => l.trim())
    .filter(Boolean)
    .slice(0, BATCH_LIMIT)
    .map((line) => {
      const { query, quantity } = parseLine(line);
      const q = query.toLowerCase();
      const qc = compact(q);
      // Точный кат. № или CAS — без исправления опечаток (SRCH-03)
      const exact = catalogProducts.filter((x) => compact(x.catalogNumber) === qc || (x.cas && compact(x.cas) === qc));
      let candidates = exact;
      if (!candidates.length && q.length >= 3) {
        candidates = findProducts(query)
          .items.filter((m) => m.r <= 4)
          .slice(0, 5)
          .map((m) => m.p);
      }
      const status: BatchLineResult['status'] = candidates.length === 0 ? 'none' : candidates.length === 1 ? 'exact' : 'multiple';
      return { line, query, quantity: Math.max(1, Math.min(999, quantity)), status, candidates: candidates.slice(0, 5).map(toCandidate) };
    });
}
