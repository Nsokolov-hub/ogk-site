import { useTranslations } from 'next-intl';
import type { Availability } from '@/types/catalog';
import { cn } from '@/lib/cn';

/**
 * «В наличии» / «Под заказ» в правом верхнем углу окна превью (правки Григория 05.11): отступ от края окна сверху
 * равен отступу сбоку. «В наличии» — наш склад или склад поставщика, у которого мы закупаем (проверка раз в несколько
 * дней на сервере, app.catalog.competitors).
 * card — в окне превью карточки (от 480 px); inline — в колонке данных компактной карточки до 480 px, где окно
 * всего 112 px и бейдж закрыл бы банку; page — окно на странице товара.
 */
export function AvailabilityBadge({
  availability,
  place = 'card',
  className,
}: {
  availability?: Availability;
  place?: 'card' | 'inline' | 'page';
  className?: string;
}) {
  const t = useTranslations('product');
  const inStock = availability === 'in_stock';
  return (
    <span
      className={cn(
        'pointer-events-none z-[1] items-center gap-1.5 rounded-pill border bg-well/85 font-medium leading-none backdrop-blur-sm',
        place === 'card' && 'absolute right-3 top-3 hidden h-7 px-3 text-[12.5px] sm:inline-flex',
        place === 'inline' && 'mb-1.5 inline-flex h-5 w-fit px-2 text-[11px] sm:hidden',
        place === 'page' && 'absolute right-4 top-4 inline-flex h-8 px-3.5 text-[13.5px]',
        inStock ? 'border-card-green-line text-card-green' : 'border-card-line text-card-muted',
        className,
      )}
    >
      {inStock ? <span aria-hidden className="size-1.5 shrink-0 rounded-full bg-card-green" /> : null}
      {inStock ? t('inStock') : t('onOrder')}
    </span>
  );
}
