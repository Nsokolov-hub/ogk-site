'use client';

import { useTranslations } from 'next-intl';
import type { ProductPreview } from '@/types/catalog';
import { Select } from '@/components/ui/Select';

export const CUSTOM_PACKAGING = '__custom__';

/** Выбор фасовки. В окне «в 1 клик» и корзине добавляется «Своя фасовка» (5.2.2). */
export function PackagingSelect({
  product,
  value,
  onChange,
  compact,
  withCustom,
  className,
}: {
  product: ProductPreview;
  value: string;
  onChange: (value: string) => void;
  compact?: boolean;
  withCustom?: boolean;
  className?: string;
}) {
  const t = useTranslations('product');
  const options = product.packagings.map((p) => ({ value: p.id, label: p.label }));
  if (withCustom && product.customPackaging) options.push({ value: CUSTOM_PACKAGING, label: t('customPackaging') });

  return (
    <Select
      label={t('packaging')}
      hideLabel={compact}
      compact={compact}
      options={options}
      value={value}
      onChange={(e) => onChange(e.target.value)}
      className={className}
    />
  );
}
