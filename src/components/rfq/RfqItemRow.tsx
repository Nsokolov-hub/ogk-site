'use client';

import { useState } from 'react';
import { MessageSquarePlus, Trash2 } from 'lucide-react';
import { useTranslations } from 'next-intl';
import type { PackUnit } from '@/types/catalog';
import type { Analogue } from '@/types/requests';
import { CUSTOM_PACKAGING } from '@/components/product/PackagingSelect';
import { Input } from '@/components/ui/Input';
import { QuantityStepper } from '@/components/ui/QuantityStepper';
import { Select } from '@/components/ui/Select';
import { Link } from '@/i18n/navigation';
import { type RfqItem, useRfqStore } from '@/lib/rfq-store';

const UNITS: PackUnit[] = ['mg', 'g', 'ml', 'pcs'];

/**
 * Строка корзины (RFQ-02): товар, фасовка или своя фасовка, количество упаковок, аналоги, комментарий, удалить.
 * Свободная строка — поля описания, бренда, кат. № и CAS для позиции вне каталога.
 */
export function RfqItemRow({ item }: { item: RfqItem }) {
  const t = useTranslations('rfq.item');
  const tp = useTranslations('product');
  const tu = useTranslations('oneClick.units');
  const { remove, setQuantity, setAnalogue, setComment, setPackaging, updateFree } = useRfqStore.getState();
  const [showComment, setShowComment] = useState(!!item.comment);
  const [customAmount, setCustomAmount] = useState(item.customPackaging ? String(item.customPackaging.amount) : '');
  const [customUnit, setCustomUnit] = useState<PackUnit>(item.customPackaging?.unit ?? 'mg');

  const analogueOptions = (['none', 'allowed', 'requested'] as Analogue[]).map((v) => ({
    value: v,
    label: tp(v === 'none' ? 'analogueNone' : v === 'allowed' ? 'analogueAllowed' : 'analogueRequested'),
  }));
  const packOptions = [
    ...(item.packagings ?? []).map((p) => ({ value: p.id, label: p.label })),
    ...(item.customAllowed ? [{ value: CUSTOM_PACKAGING, label: tp('customPackaging') }] : []),
  ];
  const isCustom = item.packagingId === null && !item.free;

  const applyCustom = (amount: string, unit: PackUnit) => {
    const n = Number(amount.replace(',', '.'));
    if (n > 0) setPackaging(item.key, { packagingId: null, packagingLabel: `${amount.trim()} ${tu(unit)}`, customPackaging: { amount: n, unit } });
  };

  return (
    <li className="rounded-block bg-surface p-4 md:p-6">
      <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_auto] lg:items-start lg:gap-8">
        <div className="min-w-0">
          {item.free ? (
            <div className="grid gap-3 sm:grid-cols-2">
              <Input
                label={t('freeName')}
                required
                value={item.name}
                onChange={(e) => updateFree(item.key, { name: e.target.value })}
                className="sm:col-span-2"
              />
              <Input label={t('freeBrand')} value={item.brand} onChange={(e) => updateFree(item.key, { brand: e.target.value })} />
              <Input label={t('freeNumber')} value={item.catalogNumber} onChange={(e) => updateFree(item.key, { catalogNumber: e.target.value })} />
              <Input label="CAS" value={item.cas ?? ''} onChange={(e) => updateFree(item.key, { cas: e.target.value })} />
            </div>
          ) : (
            <>
              <Link href={`/product/${item.slug}/`} className="chem-wrap line-clamp-2 text-body font-medium text-text transition-colors hover:text-accent md:text-lg" title={item.name}>
                {item.name}
              </Link>
              <p className="mt-1 flex flex-wrap gap-x-4 text-small text-text-secondary">
                <span>{item.brand}</span>
                <span className="tabular-nums">
                  {tp('catalogNumber')} {item.catalogNumber}
                </span>
                {item.cas ? <span className="tabular-nums">CAS {item.cas}</span> : null}
              </p>
            </>
          )}
        </div>
        <button
          type="button"
          onClick={() => remove(item.key)}
          aria-label={t('remove', { name: item.name || t('freeRow') })}
          className="hidden size-11 place-items-center rounded-full text-text-secondary transition-colors hover:bg-surface-strong hover:text-error lg:grid"
        >
          <Trash2 aria-hidden size={20} strokeWidth={1.5} />
        </button>
      </div>

      <div className="mt-4 grid gap-4 sm:grid-cols-2 lg:grid-cols-[minmax(0,1.2fr)_auto_minmax(0,1.4fr)] lg:items-end lg:gap-6">
        {item.free ? (
          <div className="hidden lg:block" />
        ) : packOptions.length > 1 ? (
          <Select
            label={tp('packaging')}
            options={packOptions}
            value={item.packagingId ?? CUSTOM_PACKAGING}
            onChange={(e) => {
              const v = e.target.value;
              if (v === CUSTOM_PACKAGING) {
                setPackaging(item.key, { packagingId: null, packagingLabel: tp('customPackaging') });
              } else {
                setPackaging(item.key, { packagingId: v, packagingLabel: item.packagings?.find((p) => p.id === v)?.label });
              }
            }}
          />
        ) : (
          <div className="flex flex-col gap-1.5">
            <span className="text-small text-text-secondary">{tp('packaging')}</span>
            <span className="flex h-12 items-center text-body text-text md:text-lg">{item.packagingLabel ?? '—'}</span>
          </div>
        )}
        <QuantityStepper
          label={t('quantity')}
          value={item.quantity}
          onChange={(n) => setQuantity(item.key, n)}
          decreaseLabel={t('decrease')}
          increaseLabel={t('increase')}
        />
        <Select
          label={tp('analogue')}
          options={analogueOptions}
          value={item.analogue}
          onChange={(e) => setAnalogue(item.key, e.target.value as Analogue)}
          className="sm:col-span-2 lg:col-span-1"
        />
      </div>

      {isCustom ? (
        <div className="mt-4 grid max-w-[480px] grid-cols-[minmax(0,1fr)_7rem] gap-3">
          <Input
            label={t('customAmount')}
            required
            inputMode="decimal"
            autoComplete="off"
            value={customAmount}
            onChange={(e) => setCustomAmount(e.target.value)}
            onBlur={() => applyCustom(customAmount, customUnit)}
          />
          <Select
            label={t('unit')}
            options={UNITS.map((u) => ({ value: u, label: tu(u) }))}
            value={customUnit}
            onChange={(e) => {
              const u = e.target.value as PackUnit;
              setCustomUnit(u);
              applyCustom(customAmount, u);
            }}
          />
        </div>
      ) : null}

      <div className="mt-4 flex flex-wrap items-center justify-between gap-3">
        {showComment ? (
          <Input
            label={t('comment')}
            value={item.comment ?? ''}
            onChange={(e) => setComment(item.key, e.target.value)}
            placeholder={t('commentPlaceholder')}
            className="w-full"
          />
        ) : (
          <button
            type="button"
            onClick={() => setShowComment(true)}
            className="inline-flex h-10 items-center gap-2 rounded-pill px-3 text-small font-medium text-accent transition-colors hover:bg-surface-strong"
          >
            <MessageSquarePlus aria-hidden size={18} strokeWidth={1.5} />
            {t('addComment')}
          </button>
        )}
        <button
          type="button"
          onClick={() => remove(item.key)}
          className="inline-flex h-10 items-center gap-2 rounded-pill px-3 text-small font-medium text-text-secondary transition-colors hover:bg-surface-strong hover:text-error lg:hidden"
        >
          <Trash2 aria-hidden size={18} strokeWidth={1.5} />
          {t('removeShort')}
        </button>
      </div>
    </li>
  );
}
