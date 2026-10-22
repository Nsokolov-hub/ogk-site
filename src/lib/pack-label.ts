import type { Packaging, ProductPreview } from '@/types/catalog';

/**
 * Подписи фасовок на языке страницы. В данных подпись русская («100 мг», «1 шт.»), ключ фасовки — в конце id
 * (p1-100-mg, c12-2-5-l). Для EN подпись собирается из ключа, чтобы на английских страницах не было кириллицы.
 */
const UNITS_EN: Record<string, string> = { mg: 'mg', g: 'g', ml: 'mL', l: 'L', pcs: 'pcs' };

export const packKey = (id: string) => id.replace(/^[a-z]*\d+-/, '');

export function packLabel(p: Pick<Packaging, 'id' | 'label'>, locale: string): string {
  if (locale === 'ru') return p.label;
  const m = packKey(p.id).match(/^(\d+(?:-\d+)?)-(mg|g|ml|l|pcs|vial|pack)$/);
  if (!m) return p.label;
  const n = m[1].replace('-', '.');
  const one = Number(n) === 1;
  if (m[2] === 'vial') return one ? '1 vial' : `${n} vials`;
  if (m[2] === 'pack') return one ? '1 pack' : `${n} packs`;
  return `${n} ${UNITS_EN[m[2]]}`;
}

/** Служебный бренд «Разные производители» у референтных препаратов */
const VARIOUS_EN = 'Various manufacturers';

/** Позиция с подписями фасовок (и служебного бренда) на языке страницы */
export function localizeProduct<T extends ProductPreview>(p: T, locale: string): T {
  if (locale === 'ru') return p;
  return {
    ...p,
    brand: p.brand.slug === 'various' ? { ...p.brand, name: VARIOUS_EN } : p.brand,
    packagings: p.packagings.map((x) => ({ ...x, label: packLabel(x, locale) })),
  };
}
