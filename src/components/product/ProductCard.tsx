'use client';

import { useState } from 'react';
import { useTranslations } from 'next-intl';
import type { ProductPreview } from '@/types/catalog';
import { Link } from '@/i18n/navigation';
import { cn } from '@/lib/cn';
import { AddToRfqButton } from './AddToRfqButton';
import { OneClickButton } from './OneClickButton';
import { PackagingSelect } from './PackagingSelect';
import { ProductImage } from './ProductImage';

const IMAGE_SIZES = {
  sm: '(min-width: 1280px) 340px, (min-width: 1024px) 30vw, (min-width: 480px) 45vw, 90vw',
  md: '(min-width: 1280px) 400px, (min-width: 768px) 45vw, 90vw',
};

/**
 * Превью товара (ТЗ 5.3). Цен и статуса наличия нет: все товары под заказ.
 * sm — маленькая для главной (4 в ряд), md — средняя для каталога (3 в ряд).
 */
export function ProductCard({
  product,
  size = 'sm',
  place = 'list',
  priority,
}: {
  product: ProductPreview;
  size?: 'sm' | 'md';
  place?: 'list' | 'search' | 'card';
  priority?: boolean;
}) {
  const t = useTranslations('product');
  const [packagingId, setPackagingId] = useState<string | null>(product.packagings[0]?.id ?? null);
  const titleId = `pc-${product.id}`;
  const numberLabel = product.cardType === 'equipment' ? t('partNumber') : t('catalogNumber');

  // До 480 px — компактная карточка: картинка слева, данные справа, кнопки на всю ширину снизу
  return (
    <article
      aria-labelledby={titleId}
      className="relative grid h-full grid-cols-[96px_minmax(0,1fr)] gap-x-3 rounded-card bg-surface p-3 transition-colors duration-300 hover:bg-surface-strong sm:flex sm:flex-col sm:p-4 md:rounded-block md:p-5"
    >
      <div className="relative w-full self-start">
        <ProductImage product={product} sizes={IMAGE_SIZES[size]} priority={priority} className="rounded-sm sm:rounded-field" />
      </div>

      <div className="flex min-w-0 flex-1 flex-col sm:mt-4">
        {/* У «Разных производителей» нет страницы бренда — без ссылки, чтобы не было битых URL */}
        {product.brand.slug === 'various' ? (
          <span className="w-fit text-small text-text-secondary">{product.brand.name}</span>
        ) : (
          <Link
            href={`/brands/${product.brand.slug}/`}
            className="relative z-10 w-fit text-small text-text-secondary transition-colors hover:text-accent"
          >
            {product.brand.name}
          </Link>
        )}

        {/* Ссылка растянута на всю карточку через ::after; кнопки и селект лежат выше (z-10) */}
        <h3 id={titleId} className="mt-1.5 text-body font-medium text-text">
          <Link
            href={`/product/${product.slug}/`}
            title={product.name}
            className="chem-wrap line-clamp-2 transition-colors after:absolute after:inset-0 after:rounded-[inherit] after:content-[''] hover:text-accent"
          >
            {product.name}
          </Link>
        </h3>

        <dl className="mt-3 grid gap-1 text-small">
          <div className="flex gap-1.5">
            <dt className="text-text-secondary">{numberLabel}</dt>
            <dd className="tabular-nums text-text">{product.catalogNumber}</dd>
          </div>
          {product.cas ? (
            <div className="flex gap-1.5">
              <dt className="text-text-secondary">CAS</dt>
              <dd className="tabular-nums text-text">{product.cas}</dd>
            </div>
          ) : null}
          {product.packagings.length === 1 ? (
            <div className="flex gap-1.5">
              <dt className="text-text-secondary">{t('packaging')}</dt>
              <dd className="text-text">{product.packagings[0].label}</dd>
            </div>
          ) : null}
        </dl>

        {product.packagings.length > 1 ? (
          <PackagingSelect
            product={product}
            value={packagingId ?? ''}
            onChange={setPackagingId}
            compact
            className="relative z-10 mt-3"
          />
        ) : null}

        {product.customPackaging ? <p className="mt-2 text-small text-accent">{t('anyPackaging')}</p> : null}
      </div>

      <div
        className={cn(
          'relative z-10 col-span-2 mt-3 flex gap-2 sm:mt-0 sm:pt-4',
          'flex-row sm:flex-col',
        )}
      >
        <AddToRfqButton product={product} packagingId={packagingId} place={place} className="min-w-0 flex-1 px-3 sm:flex-none sm:px-6" />
        <OneClickButton product={product} packagingId={packagingId} className="min-w-0 flex-1 px-3 sm:flex-none sm:px-6" />
      </div>
    </article>
  );
}

/** Скелет карточки на время загрузки */
export function ProductCardSkeleton() {
  return (
    <div aria-hidden className="flex h-full animate-pulse flex-col rounded-card bg-surface p-3 sm:p-4 md:rounded-block md:p-5">
      <div className="aspect-square rounded-field bg-surface-strong" />
      <div className="mt-4 h-3 w-16 rounded-pill bg-surface-strong" />
      <div className="mt-3 h-4 w-11/12 rounded-pill bg-surface-strong" />
      <div className="mt-2 h-4 w-2/3 rounded-pill bg-surface-strong" />
      <div className="mt-4 h-3 w-1/2 rounded-pill bg-surface-strong" />
      <div className="mt-6 h-10 rounded-pill bg-surface-strong" />
      <div className="mt-2 h-10 rounded-pill bg-surface-strong" />
    </div>
  );
}
