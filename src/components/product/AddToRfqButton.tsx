'use client';

import { useEffect, useRef, useState } from 'react';
import { Check } from 'lucide-react';
import { useTranslations } from 'next-intl';
import type { ProductPreview } from '@/types/catalog';
import { Button, type ButtonSize, type ButtonVariant } from '@/components/ui/Button';
import { track } from '@/lib/analytics';
import { cn } from '@/lib/cn';
import { openCartDrawer } from '@/lib/cart-drawer';
import { rfqKey, useRfqStore } from '@/lib/rfq-store';

/** «В корзину» → «В корзине» (открывает панель корзины, без JS — /rfq/). Состояние берётся из стора и переживает перезагрузку. */
export function AddToRfqButton({
  product,
  packagingId,
  place,
  size = 's',
  variant = 'primary',
  inCartVariant = 'menu',
  className,
}: {
  product: ProductPreview;
  packagingId: string | null;
  place: 'list' | 'card' | 'search';
  size?: ButtonSize;
  /** Вид кнопки «В корзину» и состояния «В корзине»: в карточке — контур, после добавления — заливка */
  variant?: ButtonVariant;
  inCartVariant?: ButtonVariant;
  className?: string;
}) {
  const t = useTranslations('product');
  const key = rfqKey(product.id, packagingId);
  const inCart = useRfqStore((s) => s.items.some((i) => i.key === key));
  const add = useRfqStore((s) => s.add);
  const [announcement, setAnnouncement] = useState('');
  const justAdded = useRef(false);
  const linkWrapRef = useRef<HTMLSpanElement>(null);

  // После добавления кнопка превращается в ссылку — переносим на неё фокус, чтобы он не потерялся
  useEffect(() => {
    if (inCart && justAdded.current) {
      justAdded.current = false;
      linkWrapRef.current?.querySelector('a')?.focus({ preventScroll: true });
    }
  }, [inCart]);

  const handleAdd = () => {
    const pk = product.packagings.find((p) => p.id === packagingId);
    add({
      productId: product.id,
      slug: product.slug,
      name: product.name,
      brand: product.brand.name,
      catalogNumber: product.catalogNumber,
      cas: product.cas,
      categorySlug: product.categorySlug,
      packagings: product.packagings,
      customAllowed: product.customPackaging,
      packagingId,
      packagingLabel: pk?.label,
      quantity: 1,
      analogue: product.discontinued ? 'requested' : 'none',
    });
    justAdded.current = true;
    setAnnouncement(t('added', { name: product.name }));
    track('add_to_rfq', { sku: product.catalogNumber, brand: product.brand.name, place });
  };

  return (
    <>
      {inCart ? (
        <span ref={linkWrapRef} className="contents">
          <Button href="/rfq/" onClick={openCartDrawer} aria-haspopup="dialog" variant={inCartVariant} size={size} className={cn('w-full', className)} iconStart={<Check aria-hidden size={18} strokeWidth={2} />}>
            {t('inRfq')}
          </Button>
        </span>
      ) : (
        <Button variant={variant} size={size} className={cn('w-full', className)} onClick={handleAdd}>
          {t('addToRfq')}
        </Button>
      )}
      <span role="status" aria-live="polite" className="sr-only">
        {announcement}
      </span>
    </>
  );
}
