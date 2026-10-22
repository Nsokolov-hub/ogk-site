'use client';

import { useState } from 'react';
import { useTranslations } from 'next-intl';
import type { ProductPreview } from '@/types/catalog';
import { Link } from '@/i18n/navigation';
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

  // Карточка по эталону заказчика: подложка #202320 с контуром, окно превью с флаконом, бренд, название,
  // кат. № / CAS / фасовка и контурная кнопка «В корзину». До 480 px — компактно: превью слева, данные справа.
  return (
    <article
      aria-labelledby={titleId}
      className="group relative grid h-full grid-cols-[112px_minmax(0,1fr)] gap-x-3.5 rounded-[22px] border border-card-line bg-card p-3 text-white sm:flex sm:flex-col sm:p-4" // taste-skill-ignore: контур карточки — из утверждённого эталона
    >
      <div className="relative w-full self-start">
        <ProductImage product={product} sizes={IMAGE_SIZES[size]} priority={priority} className="rounded-xl sm:rounded-2xl" />
      </div>

      <div className="flex min-w-0 flex-1 flex-col sm:mt-4">
        {/* У «Разных производителей» нет страницы бренда — без ссылки, чтобы не было битых URL */}
        {product.brand.slug === 'various' ? (
          <span className="mb-1 w-fit text-[12px] uppercase text-card-muted">{product.brand.name}</span>
        ) : (
          <Link
            href={`/brands/${product.brand.slug}/`}
            className="relative z-10 mb-1 w-fit text-[12px] uppercase text-card-muted transition-colors hover:text-card-green" // taste-skill-ignore: подпись бренда капсом — по эталону
          >
            {product.brand.name}
          </Link>
        )}

        {/* Ссылка растянута на всю карточку через ::after; кнопки и селект лежат выше (z-10) */}
        <h3 id={titleId} className="mb-3 text-[17px] font-semibold leading-[1.3] text-white sm:text-[20px]">
          <Link
            href={`/product/${product.slug}/`}
            title={product.name}
            className="chem-wrap line-clamp-2 transition-colors after:absolute after:inset-0 after:rounded-[inherit] after:content-[''] hover:text-card-green"
          >
            {product.name}
          </Link>
        </h3>

        <dl className="text-[13.5px] leading-[1.6] text-card-text">
          <div className="flex">
            <dt className="mr-1 text-card-muted">{numberLabel}</dt>
            <dd className="tabular-nums">{product.catalogNumber}</dd>
          </div>
          {product.cas ? (
            <div className="flex">
              <dt className="mr-1 text-card-muted">CAS</dt>
              <dd className="tabular-nums">{product.cas}</dd>
            </div>
          ) : null}
          {product.packagings.length === 1 ? (
            <div className="flex">
              <dt className="mr-1 text-card-muted">{t('packaging')}</dt>
              <dd>{product.packagings[0].label}</dd>
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

        {product.customPackaging ? <p className="mt-2 text-[13.5px] text-card-green">{t('anyPackaging')}</p> : null}
      </div>

      {/* «В корзину» по эталону; «в 1 клик» — тихая ссылка под кнопкой (обязательна по ТЗ 5.3) */}
      <div className="relative z-10 col-span-2 mt-3 flex items-center gap-2 sm:mt-0 sm:flex-col sm:items-stretch sm:gap-0.5 sm:pt-4">
        <AddToRfqButton
          product={product}
          packagingId={packagingId}
          place={place}
          variant="card"
          inCartVariant="cardActive"
          className="h-10 min-w-0 flex-1 px-3 text-[14px] font-medium sm:flex-none sm:px-3 sm:text-[14px]"
        />
        <OneClickButton
          product={product}
          packagingId={packagingId}
          variant="ghost"
          className="h-10 w-auto shrink-0 px-2 text-[13px] font-medium text-card-muted hover:text-card-green sm:h-8 sm:w-full sm:px-0 sm:text-[13px]"
        />
      </div>
    </article>
  );
}

/** Скелет карточки на время загрузки */
export function ProductCardSkeleton() {
  return (
    <div
      aria-hidden
      className="flex h-full animate-pulse flex-col rounded-[22px] border border-card-line bg-card p-3 sm:p-4" /* taste-skill-ignore: скелет на время загрузки повторяет эталонную карточку */
    >
      <div className="aspect-square rounded-2xl bg-well" />
      <div className="mt-4 h-3 w-14 rounded-pill bg-surface-strong" />
      <div className="mt-2 h-5 w-11/12 rounded-pill bg-surface-strong" />
      <div className="mt-2 h-5 w-2/3 rounded-pill bg-surface-strong" />
      <div className="mt-4 h-3 w-1/2 rounded-pill bg-surface-strong" />
      <div className="mt-5 h-10 rounded-lg bg-surface-strong" />
    </div>
  );
}
