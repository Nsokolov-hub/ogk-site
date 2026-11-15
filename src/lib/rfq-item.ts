import type { ProductPreview } from '@/types/catalog';
import type { SiteRequestItem } from '@/types/requests';
import { CUSTOM_PACKAGING, type ProductSelection } from './product-selection';
import type { RfqItemInput } from './rfq-store';

/** Preserve the selected pack SKU and the verified issuer, while retaining the sales channel as context. */
export function itemFromProduct(
  product: ProductPreview,
  selection: ProductSelection,
  locale = 'ru',
  customPackagingLabel?: string,
): RfqItemInput {
  const pack = product.packagings.find((p) => p.id === selection.packagingId);
  const custom = selection.packagingId === CUSTOM_PACKAGING;
  const amount = Number(selection.customAmount.replace(',', '.'));
  const identity = product.identity;
  const channel = identity && identity.supplyChannel !== identity.manufacturer
    ? `${locale === 'en' ? 'Catalog channel' : 'Канал каталога'}: ${identity.supplyChannel}`
    : undefined;
  return {
    productId: product.id,
    slug: product.slug,
    name: product.name,
    brand: identity?.manufacturer ?? product.brand.name,
    catalogNumber: pack?.catalogNumber ?? product.catalogNumber,
    baseCatalogNumber: product.catalogNumber,
    cas: product.cas,
    categorySlug: product.categorySlug,
    packagings: product.packagings,
    customAllowed: product.customPackaging,
    packagingId: custom ? null : selection.packagingId || null,
    packagingLabel: custom ? customPackagingLabel : pack?.label,
    customPackaging: custom && amount > 0 ? { amount, unit: selection.customUnit } : undefined,
    quantity: selection.quantity,
    analogue: selection.analogue,
    comment: channel,
  };
}

export function requestItemFromProduct(
  product: ProductPreview,
  selection: ProductSelection,
  locale: string,
  pageUrl: string,
  customPackagingLabel?: string,
): SiteRequestItem {
  const item = itemFromProduct(product, selection, locale, customPackagingLabel);
  return {
    siteProductId: item.productId,
    brand: item.brand,
    catalogNumber: item.catalogNumber,
    cas: item.cas,
    name: item.name,
    packaging: item.packagingLabel,
    quantity: item.quantity,
    unit: 'pack',
    analogue: item.analogue,
    customPackaging: selection.packagingId === CUSTOM_PACKAGING,
    comment: item.comment,
    pageUrl,
  };
}
