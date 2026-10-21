'use client';

import { useState } from 'react';
import Image from 'next/image';
import type { ProductPreview } from '@/types/catalog';
import { cn } from '@/lib/cn';
import { VialPlaceholder } from './VialPlaceholder';

/** Изображение товара: фото производителя → 2D-структура → фирменная заглушка-флакон */
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
    <div className={cn('relative aspect-square overflow-hidden rounded-field bg-surface-raised', className)}>
      {img && !failed ? (
        <Image
          src={img.src}
          alt={img.alt}
          fill
          sizes={sizes}
          priority={priority}
          unoptimized={img.src.endsWith('.svg')}
          onError={() => setFailed(true)}
          className={cn('object-contain', img.kind === 'structure' ? 'p-[14%]' : 'p-3')}
        />
      ) : (
        <VialPlaceholder name={product.name} cas={product.cas} brand={product.brand.name} className="absolute inset-0 p-2" />
      )}
    </div>
  );
}
