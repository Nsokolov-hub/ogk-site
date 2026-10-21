'use client';

import { useEffect, useId, useRef, useState } from 'react';
import { Check, Phone } from 'lucide-react';
import { useTranslations } from 'next-intl';
import type { PackUnit, ProductPreview } from '@/types/catalog';
import type { Analogue } from '@/types/requests';
import { TrackedLink } from '@/components/layout/TrackedLink';
import { AnalogueChoice } from '@/components/product/AnalogueChoice';
import { CUSTOM_PACKAGING } from '@/components/product/PackagingSelect';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { QuantityStepper } from '@/components/ui/QuantityStepper';
import { Select } from '@/components/ui/Select';
import { track } from '@/lib/analytics';
import { cn } from '@/lib/cn';
import { useOneClickStore } from '@/lib/one-click-store';
import { rfqKey, useRfqStore } from '@/lib/rfq-store';

const UNITS: PackUnit[] = ['mg', 'g', 'ml', 'pcs'];

/**
 * Таблица фасовок и действия карточки (ТЗ 5.4, 5.2.2, RFQ-12): фасовка или своя фасовка, количество упаковок,
 * выбор аналогов, «В корзину» и «Заказать в 1 клик», телефон с целью click_phone. Цен нет: все позиции под заказ.
 */
export function ProductOrderPanel({
  product,
  phone,
  className,
}: {
  product: ProductPreview;
  phone: { display: string; href: string };
  className?: string;
}) {
  const t = useTranslations('productPage.order');
  const tu = useTranslations('oneClick.units');
  const uid = useId().replace(/[^a-zA-Z0-9_-]/g, '');
  const [packagingId, setPackagingId] = useState<string>(product.packagings[0]?.id ?? CUSTOM_PACKAGING);
  const [customAmount, setCustomAmount] = useState('');
  const [customUnit, setCustomUnit] = useState<PackUnit>('mg');
  const [customError, setCustomError] = useState<string>();
  const [quantity, setQuantity] = useState(1);
  const [analogue, setAnalogue] = useState<Analogue>(product.discontinued ? 'requested' : 'none');
  const [announcement, setAnnouncement] = useState('');
  const justAdded = useRef(false);
  const linkWrapRef = useRef<HTMLSpanElement>(null);

  const isCustom = packagingId === CUSTOM_PACKAGING;
  const key = rfqKey(product.id, isCustom ? null : packagingId);
  const inCart = useRfqStore((s) => s.hydrated && s.items.some((i) => i.key === key));
  const add = useRfqStore((s) => s.add);
  const openOneClick = useOneClickStore((s) => s.open);

  useEffect(() => {
    if (inCart && justAdded.current) {
      justAdded.current = false;
      linkWrapRef.current?.querySelector('a')?.focus({ preventScroll: true });
    }
  }, [inCart]);

  const options = [
    ...product.packagings.map((p) => ({ id: p.id, label: p.label, note: p.catalogNumber })),
    ...(product.customPackaging ? [{ id: CUSTOM_PACKAGING, label: t('custom'), note: undefined }] : []),
  ];
  const single = options.length === 1;

  const handleAdd = () => {
    const amount = Number(customAmount.replace(',', '.'));
    if (isCustom && !(amount > 0)) {
      setCustomError(t('customError'));
      document.getElementById(`${uid}-amount`)?.focus();
      return;
    }
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
      packagingId: isCustom ? null : packagingId,
      packagingLabel: isCustom ? `${customAmount.trim()} ${tu(customUnit)}` : pk?.label,
      customPackaging: isCustom ? { amount, unit: customUnit } : undefined,
      quantity,
      analogue,
    });
    justAdded.current = true;
    setAnnouncement(t('added'));
    track('add_to_rfq', { sku: product.catalogNumber, brand: product.brand.name, place: 'card' });
  };

  return (
    <section aria-labelledby={`${uid}-title`} className={cn('rounded-block bg-surface p-5 md:p-7', className)}>
      <h2 id={`${uid}-title`} className="text-h4 font-medium text-text">
        {t('title')}
      </h2>

      {/* Фасовки: одна — одной строкой; несколько или своя — выбор */}
      {single && !isCustom ? (
        <p className="mt-4 flex items-baseline justify-between gap-4 rounded-field bg-surface-strong px-4 py-3 text-body text-text">
          <span>{options[0].label}</span>
          {options[0].note ? <span className="text-small tabular-nums text-text-secondary">{t('packNumber', { n: options[0].note })}</span> : null}
        </p>
      ) : (
        <fieldset className="mt-4">
          <legend className="sr-only">{t('packaging')}</legend>
          <div className="flex flex-wrap gap-2">
            {options.map((o) => {
              const checked = o.id === packagingId;
              return (
                <label
                  key={o.id}
                  className={cn(
                    'relative inline-flex min-h-11 cursor-pointer items-center gap-2 rounded-pill px-4 text-body transition-colors',
                    'has-[:focus-visible]:outline-2 has-[:focus-visible]:outline-offset-2 has-[:focus-visible]:outline-accent',
                    checked ? 'bg-accent text-text-on-accent' : 'bg-surface-strong text-text hover:text-accent',
                  )}
                >
                  <input
                    type="radio"
                    name={`${uid}-pack`}
                    value={o.id}
                    checked={checked}
                    onChange={() => {
                      setPackagingId(o.id);
                      setCustomError(undefined);
                    }}
                    className="sr-only"
                  />
                  {checked ? <Check aria-hidden size={16} strokeWidth={2} /> : null}
                  {o.label}
                </label>
              );
            })}
          </div>
        </fieldset>
      )}

      {isCustom ? (
        <div className="mt-4 grid grid-cols-[minmax(0,1fr)_7rem] gap-3">
          <Input
            id={`${uid}-amount`}
            label={t('amount')}
            required
            inputMode="decimal"
            autoComplete="off"
            value={customAmount}
            error={customError}
            onChange={(e) => {
              setCustomAmount(e.target.value);
              setCustomError(undefined);
            }}
          />
          <Select
            label={t('unit')}
            options={UNITS.map((u) => ({ value: u, label: tu(u) }))}
            value={customUnit}
            onChange={(e) => setCustomUnit(e.target.value as PackUnit)}
          />
        </div>
      ) : null}

      <div className="mt-6 grid gap-6 sm:grid-cols-[auto_minmax(0,1fr)] sm:gap-10">
        <QuantityStepper
          label={t('quantity')}
          value={quantity}
          onChange={setQuantity}
          decreaseLabel={t('decrease')}
          increaseLabel={t('increase')}
        />
        <AnalogueChoice name={`${uid}-analogue`} value={analogue} onChange={setAnalogue} />
      </div>

      <div className="mt-7 grid gap-2 sm:grid-cols-2">
        {inCart ? (
          <span ref={linkWrapRef} className="contents">
            <Button href="/rfq/" variant="menu" size="m" iconStart={<Check aria-hidden size={18} strokeWidth={2} />}>
              {t('inCart')}
            </Button>
          </span>
        ) : (
          <Button size="m" onClick={handleAdd}>
            {t('add')}
          </Button>
        )}
        <Button
          variant="secondary"
          size="m"
          aria-haspopup="dialog"
          onClick={(e) => openOneClick({ product, packagingId: isCustom ? null : packagingId, trigger: e.currentTarget })}
        >
          {t('oneClick')}
        </Button>
      </div>
      <span role="status" aria-live="polite" className="sr-only">
        {announcement}
      </span>

      <p className="mt-4 text-small text-text-secondary">{t('note')}</p>
      <TrackedLink
        href={phone.href}
        event="click_phone"
        params={{ place: 'product' }}
        className="mt-3 inline-flex items-center gap-2 text-body font-medium text-text transition-colors hover:text-accent"
      >
        <Phone aria-hidden size={18} strokeWidth={1.5} className="text-accent" />
        {phone.display}
      </TrackedLink>
    </section>
  );
}
