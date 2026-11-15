import type { PackUnit, ProductPreview } from '@/types/catalog';
import type { Analogue } from '@/types/requests';

export const CUSTOM_PACKAGING = '__custom__';

/** The buyer's complete choice, shared by the product panel and its quick-request entry points. */
export interface ProductSelection {
  packagingId: string;
  quantity: number;
  analogue: Analogue;
  customAmount: string;
  customUnit: PackUnit;
}

export function defaultProductSelection(product: ProductPreview, packagingId?: string | null): ProductSelection {
  return {
    packagingId: packagingId ?? product.packagings[0]?.id ?? (product.customPackaging ? CUSTOM_PACKAGING : ''),
    quantity: 1,
    analogue: product.discontinued ? 'requested' : 'none',
    customAmount: '',
    customUnit: 'mg',
  };
}
