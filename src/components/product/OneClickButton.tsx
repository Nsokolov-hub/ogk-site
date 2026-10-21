'use client';

import { useTranslations } from 'next-intl';
import type { ProductPreview } from '@/types/catalog';
import { Button, type ButtonSize } from '@/components/ui/Button';
import { cn } from '@/lib/cn';
import { useOneClickStore } from '@/lib/one-click-store';

export function OneClickButton({
  product,
  packagingId,
  size = 's',
  className,
}: {
  product: ProductPreview;
  packagingId: string | null;
  size?: ButtonSize;
  className?: string;
}) {
  const t = useTranslations('product');
  const open = useOneClickStore((s) => s.open);
  return (
    <Button
      variant="secondary"
      size={size}
      aria-haspopup="dialog"
      className={cn('w-full', className)}
      onClick={(e) => open({ product, packagingId, trigger: e.currentTarget })}
    >
      {t('oneClick')}
    </Button>
  );
}
