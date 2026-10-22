'use client';

import { useState } from 'react';
import Image from 'next/image';
import type { ProductPreview } from '@/types/catalog';
import { cn } from '@/lib/cn';
import { VialPlaceholder } from './VialPlaceholder';

/**
 * Изображение товара: фото производителя → 2D-структура → фирменная заглушка-флакон.
 * Окно превью по эталону: тёмный фон, скругление 16 px, флакон 88 % по центру с отступом сверху 14 px.
 * У флакона свечение нарисовано в самом SVG; фото и структуре даём такое же свечение фоном окна.
 */
export function ProductImage({
  product,
  sizes,
  priority,
  className,
}: {
  product: ProductPreview;
  sizes: string;
  priority?: boolean;
  className?: string;
}) {
  const [failed, setFailed] = useState(false);
  const img = product.image;

  return (
    <div className={cn('relative isolate aspect-square overflow-hidden rounded-2xl bg-well', className)}>
      {img && !failed ? (
        <>
          <span
            aria-hidden
            className="absolute inset-0 -z-10 bg-[radial-gradient(circle_at_50%_52%,var(--color-glow),transparent_40%)]" // taste-skill-ignore: то же свечение, что у флакона в эталоне
          />
          <Image
            src={img.src}
            alt={img.alt}
            fill
            sizes={sizes}
            priority={priority}
            unoptimized={img.src.endsWith('.svg')}
            onError={() => setFailed(true)}
            className={cn('object-contain', img.kind === 'structure' ? 'p-[16%] pt-[calc(16%+14px)]' : 'p-3 pt-[26px]')}
          />
        </>
      ) : (
        <div className="absolute inset-0 flex items-center justify-center pt-[14px]">
          <VialPlaceholder
            name={product.name}
            cas={product.cas}
            brand={product.brand.name}
            code={product.catalogNumber}
            className="h-[88%] w-[88%]"
          />
        </div>
      )}
    </div>
  );
}
