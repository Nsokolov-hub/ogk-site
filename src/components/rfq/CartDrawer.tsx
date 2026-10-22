'use client';

import { useEffect } from 'react';
import * as RD from '@radix-ui/react-dialog';
import { ListPlus, ShoppingCart, Trash2, X } from 'lucide-react';
import { useTranslations } from 'next-intl';
import { Button } from '@/components/ui/Button';
import { QuantityStepper } from '@/components/ui/QuantityStepper';
import { Link, usePathname } from '@/i18n/navigation';
import { useCartDrawer } from '@/lib/cart-drawer';
import { type RfqItem, useRfqStore } from '@/lib/rfq-store';

/**
 * Выдвижная панель корзины запроса (RFQ-01, ТЗ 11.3): состав, количество, удаление и переход к оформлению.
 * Фасовку, аналоги и комментарии меняют на странице /rfq/ — панель остаётся короткой.
 */
export function CartDrawer() {
  const t = useTranslations('cartDrawer');
  const open = useCartDrawer((s) => s.open);
  const setOpen = useCartDrawer((s) => s.setOpen);
  const items = useRfqStore((s) => s.items);
  const hydrated = useRfqStore((s) => s.hydrated);
  const pathname = usePathname();
  const close = () => setOpen(false);

  // Переход на другую страницу закрывает панель
  useEffect(() => {
    setOpen(false);
  }, [pathname, setOpen]);

  const packs = items.reduce((n, i) => n + i.quantity, 0);

  return (
    <RD.Root open={open} onOpenChange={setOpen}>
      <RD.Portal>
        <RD.Overlay className="fixed inset-0 z-[200] bg-base-deep/70 backdrop-blur-sm data-[state=open]:animate-fade-in" />
        <RD.Content
          className="fixed inset-y-0 right-0 z-[201] flex w-full max-w-[460px] flex-col bg-surface-raised text-text shadow-[0_24px_80px_rgb(0_0_0/0.5)] outline-none data-[state=open]:animate-drawer-in sm:rounded-l-block" // taste-skill-ignore: панель поверх страницы
        >
          <div className="flex items-start justify-between gap-4 px-5 pb-3 pt-5 md:px-7 md:pt-7">
            <div className="min-w-0">
              <RD.Title className="text-h3 font-medium">{t('title')}</RD.Title>
              <RD.Description className="mt-1 text-small text-text-secondary">
                {hydrated && items.length ? t('summary', { items: items.length, packs }) : t('note')}
              </RD.Description>
            </div>
            <RD.Close
              aria-label={t('close')}
              className="-mr-2 -mt-1 grid size-11 shrink-0 place-items-center rounded-full text-text-secondary transition-colors hover:text-text"
            >
              <X aria-hidden size={22} strokeWidth={1.5} />
            </RD.Close>
          </div>

          {hydrated && items.length ? (
            <>
              <ul className="flex flex-1 flex-col gap-2 overflow-y-auto overscroll-contain px-5 pb-4 md:px-7">
                {items.map((item) => (
                  <DrawerItem key={item.key} item={item} onNavigate={close} />
                ))}
              </ul>
              <div className="bg-surface px-5 pb-6 pt-5 md:px-7">
                <p className="text-small text-text-secondary">{t('note')}</p>
                <Button href="/rfq/" size="m" className="mt-4 w-full" onClick={close}>
                  {t('checkout')}
                </Button>
                <Button variant="ghost" size="m" className="mt-1 w-full" onClick={close}>
                  {t('continue')}
                </Button>
              </div>
            </>
          ) : (
            <div className="flex flex-1 flex-col items-start gap-4 px-5 pb-8 pt-4 md:px-7">
              <span className="grid size-14 place-items-center rounded-full bg-surface-strong text-accent">
                <ShoppingCart aria-hidden size={26} strokeWidth={1.5} />
              </span>
              <p className="text-h4 font-medium text-text">{t('empty.title')}</p>
              <p className="text-body text-text-secondary">{t('empty.text')}</p>
              <div className="mt-2 flex w-full flex-col gap-2">
                <Button href="/catalog/" size="m" className="w-full" onClick={close}>
                  {t('empty.catalog')}
                </Button>
                <Button
                  href="/rfq/#bulk"
                  variant="secondary"
                  size="m"
                  className="w-full"
                  onClick={close}
                  iconStart={<ListPlus aria-hidden size={20} strokeWidth={1.5} />}
                >
                  {t('empty.bulk')}
                </Button>
              </div>
            </div>
          )}
        </RD.Content>
      </RD.Portal>
    </RD.Root>
  );
}

function DrawerItem({ item, onNavigate }: { item: RfqItem; onNavigate: () => void }) {
  const t = useTranslations('cartDrawer');
  const tp = useTranslations('product');
  const setQuantity = useRfqStore((s) => s.setQuantity);
  const remove = useRfqStore((s) => s.remove);
  const name = item.name || t('freeRow');
  const meta = [item.brand, item.catalogNumber ? `${tp('catalogNumber')} ${item.catalogNumber}` : '', item.cas ? `CAS ${item.cas}` : '']
    .filter(Boolean)
    .join(' · ');

  return (
    <li className="rounded-card bg-surface p-4">
      <div className="flex items-start gap-2">
        <div className="min-w-0 flex-1">
          {item.free || !item.slug ? (
            <p className="chem-wrap line-clamp-2 text-body font-medium text-text" title={name}>
              {name}
            </p>
          ) : (
            <Link
              href={`/product/${item.slug}/`}
              onClick={onNavigate}
              title={item.name}
              className="chem-wrap line-clamp-2 text-body font-medium text-text transition-colors hover:text-accent"
            >
              {item.name}
            </Link>
          )}
          {meta ? <p className="mt-1 text-small tabular-nums text-text-secondary">{meta}</p> : null}
        </div>
        <button
          type="button"
          onClick={() => remove(item.key)}
          aria-label={t('remove', { name })}
          className="-mr-2 -mt-2 grid size-11 shrink-0 place-items-center rounded-full text-text-secondary transition-colors hover:text-error"
        >
          <Trash2 aria-hidden size={18} strokeWidth={1.5} />
        </button>
      </div>
      <div className="mt-3 flex flex-wrap items-end justify-between gap-3">
        <div className="min-w-0">
          <p className="text-small text-text-secondary">{tp('packaging')}</p>
          <p className="mt-1 text-body text-text">{item.free ? t('freePack') : (item.packagingLabel ?? '—')}</p>
          {item.analogue !== 'none' ? (
            <p className="mt-1 text-small text-accent">{t(`analogue.${item.analogue}`)}</p>
          ) : null}
        </div>
        <QuantityStepper
          label={t('quantity')}
          value={item.quantity}
          onChange={(n) => setQuantity(item.key, n)}
          decreaseLabel={t('decrease')}
          increaseLabel={t('increase')}
        />
      </div>
    </li>
  );
}
