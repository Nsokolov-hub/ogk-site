import type { FacetKey, FacetValue } from '@/types/catalog';
import { TRANSLATED_FACETS } from '@/lib/catalog';

type T = (key: string) => string;

/** Подпись значения фильтра: перечисления — из словаря, остальное — как в данных */
export function facetValueLabel(t: T, key: FacetKey, value: Pick<FacetValue, 'value' | 'label'>): string {
  if (key === 'pack' && value.value === 'custom') return t('values.packCustom');
  if (TRANSLATED_FACETS.includes(key)) return t(`values.${key}.${value.value}`);
  return value.label;
}
