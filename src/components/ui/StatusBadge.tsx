import { useTranslations } from 'next-intl';
import type { Availability } from '@/types/catalog';
import { cn } from '@/lib/cn';

/** «В наличии» — заливка accent; «Под заказ» — контур */
export function StatusBadge({ status, className }: { status: Availability; className?: string }) {
  const t = useTranslations('product');
  return (
    <span
      className={cn(
        'inline-flex h-6 items-center whitespace-nowrap rounded-pill border px-2.5 text-caption font-medium',
        status === 'in_stock'
          ? 'border-accent bg-accent text-text-on-accent'
          : 'border-border bg-base/70 text-text-secondary backdrop-blur-sm',
        className,
      )}
    >
      {status === 'in_stock' ? t('inStock') : t('onRequest')}
    </span>
  );
}
