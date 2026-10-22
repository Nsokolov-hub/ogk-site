'use client';

import { useEffect, useRef, useState } from 'react';
import { ShoppingCart } from 'lucide-react';
import { useTranslations } from 'next-intl';
import { Link, usePathname } from '@/i18n/navigation';
import { openCartDrawer } from '@/lib/cart-drawer';
import { cn } from '@/lib/cn';
import { selectRfqCount, useRfqStore } from '@/lib/rfq-store';

/** Иконка корзины запроса со счётчиком (RFQ-01): открывает выдвижную панель. Счётчик появляется после восстановления корзины из хранилища. */
export function CartButton({ className }: { className?: string }) {
  const t = useTranslations('header');
  const count = useRfqStore(selectRfqCount);
  const hydrated = useRfqStore((s) => s.hydrated);
  const [bump, setBump] = useState(false);
  const prev = useRef(count);
  // На самой странице корзины панель не нужна
  const onRfqPage = usePathname().replace(/\/$/, '') === '/rfq';

  useEffect(() => {
    if (!hydrated) return;
    if (count > prev.current) {
      setBump(true);
      const id = window.setTimeout(() => setBump(false), 450);
      prev.current = count;
      return () => window.clearTimeout(id);
    }
    prev.current = count;
  }, [count, hydrated]);

  const visibleCount = hydrated ? count : 0;

  return (
    <Link
      href="/rfq/"
      onClick={onRfqPage ? undefined : openCartDrawer}
      aria-haspopup={onRfqPage ? undefined : 'dialog'}
      aria-label={t('cartLabel', { count: visibleCount })}
      className={cn('relative inline-grid size-11 shrink-0 place-items-center rounded-full text-text transition-colors hover:text-accent', className)}
    >
      <ShoppingCart aria-hidden size={22} strokeWidth={1.5} />
      {visibleCount > 0 ? (
        <span
          aria-hidden
          className={cn(
            'absolute -right-0.5 -top-0.5 h-5 min-w-5 rounded-pill bg-accent px-1 text-center text-[11px] font-semibold leading-5 text-text-on-accent',
            bump && 'animate-bump',
          )}
        >
          {visibleCount > 99 ? '99+' : visibleCount}
        </span>
      ) : null}
    </Link>
  );
}
