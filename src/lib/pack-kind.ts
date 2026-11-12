import type { ProductPreview } from '@/types/catalog';

/**
 * Какую тару нарисовать на карточке без фото (рисунки — public/images/products, scripts/draw-packaging.py).
 * Своих фото у нас нет, а фото производителей без их разрешения брать нельзя — поэтому иллюстрация: по разделу
 * каталога и первой фасовке. Распределение на проде 12.11.2026: биохимия — антитела, белки, плазмиды в мкл, мкг и
 * «1 шт.» (~566 тыс.); реактивы — граммы и миллиграммы (~550 тыс.), килограммы и литры (~45 тыс.); оборудование,
 * хроматография, наборы и мультиупаковки — коробки.
 */
export type PackKind = 'vial' | 'bottle' | 'jar' | 'solvent' | 'tube' | 'box';

const GRAMS: Record<string, number> = { мкг: 1e-6, ug: 1e-6, µg: 1e-6, мг: 1e-3, mg: 1e-3, г: 1, g: 1, кг: 1000, kg: 1000 };
const ML: Record<string, number> = { мкл: 1e-3, ul: 1e-3, µl: 1e-3, мл: 1, ml: 1, л: 1000, l: 1000 };
const PIECES = new Set(['шт', 'pcs', 'pc', 'piece', 'pieces']);
/** Единицы того, что продаётся не во флаконе: наборы и тесты, упаковки, метры, диски, пластины, слайды */
const BOXY = new Set(['тест', 'test', 'tests', 'набор', 'kit', 'kits', 'упак', 'pack', 'мм', 'см', 'м', 'mm', 'cm', 'm',
  'стрипов', 'слайдов', 'дисков', 'кругов', 'пластин', 'plts', 'tbs']);
/** Разделы, где всё — коробки: колонки и расходники, фармакопеи, лекарства в заводской упаковке */
const BOXED = new Set(['chromatography', 'pharmacopeias', 'reference-drugs']);

interface Amount {
  count: number;
  grams?: number;
  ml?: number;
  unit: string;
}

/** «100 мг», «6 × 500 мл», «2,5 л», «1 шт.», «96 тест.» → число упаковок, масса или объём одной, единица */
export function parsePack(label: string | undefined): Amount | null {
  const m = label?.trim().match(/^(\d+(?:[.,]\d+)?)\s*(?:[×x*]\s*(\d+(?:[.,]\d+)?)\s*)?([^\s\d.]+)/i);
  if (!m) return null;
  const num = (s: string) => Number(s.replace(',', '.'));
  const count = m[2] ? num(m[1]) : 1;
  const amount = num(m[2] ?? m[1]);
  const unit = m[3].toLowerCase().replace(/\.$/, '');
  if (unit in GRAMS) return { count, grams: amount * GRAMS[unit], unit };
  if (unit in ML) return { count, ml: amount * ML[unit], unit };
  return { count, unit };
}

export function packKind(product: Pick<ProductPreview, 'cardType' | 'categorySlug' | 'packagings'>): PackKind {
  if (product.cardType !== 'standard') return 'box';
  const [top, section] = product.categorySlug.split('/');
  if (BOXED.has(top)) return 'box';
  const pack = parsePack(product.packagings[0]?.label);
  if (pack && pack.count > 1) return 'box';
  const { grams, ml, unit } = pack ?? {};

  if (top === 'biochemistry') {
    if ((grams ?? 0) > 250) return 'jar';
    if ((ml ?? 0) > 10 || (grams ?? 0) > 5) return 'bottle';
    if (unit && BOXY.has(unit)) return 'box';
    // Клеточная биология в штуках — планшеты и флаконы для культур; плазмиды и антитела «1 шт.» — в пробирках
    if (section === 'cell-biology' && unit && PIECES.has(unit)) return 'box';
    return 'tube';
  }
  if (ml !== undefined) return ml > 250 ? 'solvent' : ml > 10 ? 'bottle' : 'vial';
  if (grams !== undefined) return grams > 250 ? 'jar' : grams > 5 ? 'bottle' : 'vial';
  // Стандартный образец «1 шт.» — ампула или флакон сертифицированного материала
  if (top === 'reference-standards' && unit && PIECES.has(unit)) return 'vial';
  // Штуки, наборы, метры: фольга, стержни, диски, планшеты. ЕД, мкмоль и флаконы — во флаконе
  if (unit && (PIECES.has(unit) || BOXY.has(unit))) return 'box';
  return 'vial';
}
