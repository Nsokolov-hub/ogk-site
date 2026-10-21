'use client';

import { useId, useMemo, useState } from 'react';
import { Check, ShoppingCart } from 'lucide-react';
import { useTranslations } from 'next-intl';
import type { ProductPreview, SubstanceRole } from '@/types/catalog';
import { Button } from '@/components/ui/Button';
import { Link } from '@/i18n/navigation';
import { track } from '@/lib/analytics';
import { cn } from '@/lib/cn';
import { rfqKey, useRfqStore } from '@/lib/rfq-store';

/**
 * Позиции субстанции с выбором нескольких строк и добавлением в корзину одним действием (ТЗ SC-05).
 * Группы: стандарты API, примеси, метаболиты, меченые соединения. Без JS — обычные ссылки на карточки.
 */
export function SubstancePicker({
  groups,
  headingLevel = 'h2',
}: {
  groups: { role: SubstanceRole; title: string; items: ProductPreview[] }[];
  headingLevel?: 'h2' | 'h3';
}) {
  const t = useTranslations('substancePage.picker');
  const tp = useTranslations('product');
  const uid = useId().replace(/[^a-zA-Z0-9_-]/g, '');
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [added, setAdded] = useState<number | null>(null);
  const add = useRfqStore((s) => s.add);
  const cartItems = useRfqStore((s) => s.items);
  const cartKeys = useMemo(() => new Set(cartItems.map((i) => i.key)), [cartItems]);
  const all = groups.flatMap((g) => g.items);
  const Heading = headingLevel;

  const toggle = (id: string) => {
    setAdded(null);
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const toggleGroup = (items: ProductPreview[], on: boolean) => {
    setAdded(null);
    setSelected((prev) => {
      const next = new Set(prev);
      for (const p of items) {
        if (on) next.add(p.id);
        else next.delete(p.id);
      }
      return next;
    });
  };

  const addSelected = () => {
    const chosen = all.filter((p) => selected.has(p.id));
    for (const p of chosen) {
      const pk = p.packagings[0];
      add({
        productId: p.id,
        slug: p.slug,
        name: p.name,
        brand: p.brand.name,
        catalogNumber: p.catalogNumber,
        cas: p.cas,
        categorySlug: p.categorySlug,
        packagings: p.packagings,
        customAllowed: p.customPackaging,
        packagingId: pk?.id ?? null,
        packagingLabel: pk?.label,
        quantity: 1,
        analogue: 'none',
      });
      track('add_to_rfq', { sku: p.catalogNumber, brand: p.brand.name, place: 'list' });
    }
    setAdded(chosen.length);
    setSelected(new Set());
  };

  return (
    <div className="flex flex-col gap-14">
      {groups.map((g) => {
        const allOn = g.items.every((p) => selected.has(p.id));
        const groupId = `${uid}-${g.role}`;
        return (
          <section key={g.role} aria-labelledby={groupId}>
            <div className="flex flex-wrap items-center justify-between gap-3">
              <Heading id={groupId} className="text-h3 font-medium text-text">
                {g.title} <span className="text-text-secondary">{g.items.length}</span>
              </Heading>
              <button
                type="button"
                onClick={() => toggleGroup(g.items, !allOn)}
                className="inline-flex h-10 items-center rounded-pill px-4 text-small font-medium text-accent transition-colors hover:bg-surface-strong"
              >
                {allOn ? t('unselectGroup') : t('selectGroup')}
              </button>
            </div>
            <ul className="mt-5 flex flex-col gap-2">
              {g.items.map((p) => {
                const checked = selected.has(p.id);
                const inCart = cartKeys.has(rfqKey(p.id, p.packagings[0]?.id ?? null));
                const cb = `${uid}-cb-${p.id}`;
                return (
                  <li
                    key={p.id}
                    className={cn(
                      'grid grid-cols-[auto_minmax(0,1fr)] items-start gap-x-4 gap-y-2 rounded-field px-4 py-3 transition-colors md:grid-cols-[auto_minmax(0,1fr)_10rem_9rem_minmax(0,11rem)] md:items-center md:px-5',
                      checked ? 'bg-accent/10' : 'bg-surface',
                    )}
                  >
                    <span className="relative mt-0.5 inline-grid size-5 place-items-center md:mt-0">
                      <input
                        id={cb}
                        type="checkbox"
                        checked={checked}
                        onChange={() => toggle(p.id)}
                        aria-label={t('select', { name: p.name })}
                        className="peer size-5 cursor-pointer appearance-none rounded-[6px] border border-text-secondary transition-colors checked:border-accent checked:bg-accent hover:border-text"
                      />
                      <Check aria-hidden size={14} strokeWidth={3} className="pointer-events-none absolute text-base opacity-0 peer-checked:opacity-100" />
                    </span>
                    <div className="min-w-0">
                      <Link href={`/product/${p.slug}/`} className="chem-wrap line-clamp-2 text-body font-medium text-text transition-colors hover:text-accent" title={p.name}>
                        {p.name}
                      </Link>
                      {inCart ? <p className="mt-1 text-small text-accent">{tp('inRfq')}</p> : null}
                    </div>
                    <p className="col-start-2 text-small text-text md:col-start-auto">
                      <span className="text-text-secondary md:sr-only">{t('brand')} </span>
                      {p.brand.name}
                    </p>
                    <p className="col-start-2 text-small tabular-nums text-text md:col-start-auto">
                      <span className="text-text-secondary">{tp('catalogNumber')} </span>
                      {p.catalogNumber}
                    </p>
                    <p className="col-start-2 text-small text-text md:col-start-auto">
                      {p.packagings.map((x) => x.label).join(' / ')}
                      {p.customPackaging ? <span className="block text-caption text-accent">{tp('anyPackaging')}</span> : null}
                    </p>
                  </li>
                );
              })}
            </ul>
          </section>
        );
      })}

      {/* Панель действия: появляется, когда что-то выбрано */}
      <div aria-live="polite" className="sticky bottom-4 z-20 empty:hidden">
        {selected.size > 0 ? (
          <div className="flex flex-wrap items-center justify-between gap-3 rounded-pill bg-surface-raised p-2 pl-6 shadow-[0_12px_40px_rgb(0_0_0/0.45)]" /* taste-skill-ignore: панель плавает над списком */>
            <p className="text-body text-text">{t('selected', { count: selected.size })}</p>
            <Button size="m" onClick={addSelected} iconStart={<ShoppingCart aria-hidden size={18} strokeWidth={1.5} />}>
              {t('addSelected')}
            </Button>
          </div>
        ) : added ? (
          <div className="flex flex-wrap items-center justify-between gap-3 rounded-pill bg-surface-raised p-2 pl-6 shadow-[0_12px_40px_rgb(0_0_0/0.45)]" /* taste-skill-ignore: панель плавает над списком */>
            <p className="text-body text-text">{t('added', { count: added })}</p>
            <Button href="/rfq/" variant="menu" size="m">
              {t('toCart')}
            </Button>
          </div>
        ) : null}
      </div>
    </div>
  );
}
