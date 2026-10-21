'use client';

import { useState } from 'react';
import { Controller, useForm, useWatch } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { useLocale, useTranslations } from 'next-intl';
import { z } from 'zod';
import type { PackUnit, ProductPreview } from '@/types/catalog';
import type { Analogue } from '@/types/requests';
import type { SiteSettings } from '@/types/settings';
import { ConsentCheckbox } from '@/components/forms/ConsentCheckbox';
import { FormStatus } from '@/components/forms/FormStatus';
import { Honeypot } from '@/components/forms/Honeypot';
import { PhoneInput } from '@/components/forms/PhoneInput';
import { Button } from '@/components/ui/Button';
import { Dialog } from '@/components/ui/Dialog';
import { Input } from '@/components/ui/Input';
import { QuantityStepper } from '@/components/ui/QuantityStepper';
import { Select } from '@/components/ui/Select';
import { submitSiteRequest } from '@/lib/api';
import { track } from '@/lib/analytics';
import { useFormMeta } from '@/lib/hooks';
import { useOneClickStore } from '@/lib/one-click-store';
import { toE164 } from '@/lib/phone';
import { fields } from '@/lib/validation';
import { AnalogueChoice } from './AnalogueChoice';
import { CUSTOM_PACKAGING, PackagingSelect } from './PackagingSelect';

const UNITS: PackUnit[] = ['mg', 'g', 'ml', 'pcs'];

const schema = z
  .object({
    packagingId: z.string(),
    customAmount: z.string(),
    customUnit: z.enum(['mg', 'g', 'ml', 'pcs']),
    quantity: z.number().int().min(1).max(999),
    analogue: z.enum(['none', 'allowed', 'requested']),
    name: fields.shortName,
    company: fields.company,
    phone: fields.phone,
    email: fields.email,
    consent: fields.consent,
    website: fields.website,
  })
  .superRefine((v, ctx) => {
    if (v.packagingId === CUSTOM_PACKAGING && !(Number(v.customAmount.replace(',', '.')) > 0)) {
      ctx.addIssue({ code: 'custom', path: ['customAmount'], message: 'positive' });
    }
  });

type Values = z.infer<typeof schema>;

/** Окно «Заказать в 1 клик» (RFQ-04): одно на приложение, открывается из любой карточки */
export function OneClickOrderDialog({ docs }: { docs: SiteSettings['docs'] }) {
  const t = useTranslations('oneClick');
  const tc = useTranslations('common');
  const { isOpen, product, packagingId, trigger, close } = useOneClickStore();
  // Новый ключ на каждое открытие — форма начинается с чистого листа
  const [session, setSession] = useState(0);
  const [lastOpen, setLastOpen] = useState(false);
  if (isOpen !== lastOpen) {
    setLastOpen(isOpen);
    if (isOpen) setSession((s) => s + 1);
  }

  return (
    <Dialog
      open={isOpen}
      onOpenChange={(o) => {
        if (!o) close();
      }}
      title={t('title')}
      closeLabel={tc('close')}
      onCloseAutoFocus={(e) => {
        if (trigger?.isConnected) {
          e.preventDefault();
          trigger.focus();
        }
      }}
    >
      {product ? (
        <OneClickForm key={session} product={product} initialPackagingId={packagingId} docs={docs} onClose={close} />
      ) : null}
    </Dialog>
  );
}

function OneClickForm({
  product,
  initialPackagingId,
  docs,
  onClose,
}: {
  product: ProductPreview;
  initialPackagingId: string | null;
  docs: SiteSettings['docs'];
  onClose: () => void;
}) {
  const t = useTranslations('oneClick');
  const tp = useTranslations('product');
  const tf = useTranslations('form');
  const te = useTranslations('errors');
  const locale = useLocale() as 'ru' | 'en';
  const { onFocusCapture, elapsedMs } = useFormMeta('one_click');
  const [result, setResult] = useState<{ number: string } | null>(null);
  const [failed, setFailed] = useState(false);

  const firstPackaging = initialPackagingId ?? product.packagings[0]?.id ?? (product.customPackaging ? CUSTOM_PACKAGING : '');

  const {
    register,
    control,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<Values>({
    resolver: zodResolver(schema),
    mode: 'onTouched',
    defaultValues: {
      packagingId: firstPackaging,
      customAmount: '',
      customUnit: 'mg',
      quantity: 1,
      analogue: (product.discontinued ? 'requested' : 'none') satisfies Analogue,
      name: '',
      company: '',
      phone: '',
      email: '',
      consent: false,
      website: '',
    },
  });

  const packagingValue = useWatch({ control, name: 'packagingId' });
  const isCustom = packagingValue === CUSTOM_PACKAGING;
  const err = (key?: string) => (key ? te(key) : undefined);
  const showPackagingSelect = product.packagings.length > 1 || product.customPackaging;
  const numberLabel = product.cardType === 'equipment' ? tp('partNumber') : tp('catalogNumber');

  const onSubmit = async (v: Values) => {
    setFailed(false);
    const pk = product.packagings.find((p) => p.id === v.packagingId);
    const custom = v.packagingId === CUSTOM_PACKAGING;
    try {
      const res = v.website
        ? { number: '—', siteRequestId: '' }
        : await submitSiteRequest({
            kind: 'one_click',
            lang: locale,
            customer: {
              name: v.name.trim(),
              company: v.company.trim(),
              phone: toE164(v.phone) ?? v.phone,
              email: v.email.trim(),
              marketingConsent: false,
            },
            items: [
              {
                siteProductId: product.id,
                brand: product.brand.name,
                catalogNumber: product.catalogNumber,
                cas: product.cas,
                name: product.name,
                packaging: custom ? `${v.customAmount} ${t(`units.${v.customUnit}`)}` : pk?.label,
                quantity: v.quantity,
                unit: 'pack',
                analogue: v.analogue,
                customPackaging: custom,
                pageUrl: window.location.href,
              },
            ],
            personalDataConsent: true,
            antispam: { website: v.website ?? '', elapsedMs: elapsedMs() },
            pageUrl: window.location.href,
          });
      track('product_request', { sku: product.catalogNumber, brand: product.brand.name, category: product.categorySlug });
      track('form_submit', { form_type: 'one_click', page: window.location.pathname });
      setResult({ number: res.number });
    } catch {
      setFailed(true);
    }
  };

  if (result) {
    return (
      <div className="flex flex-col gap-6">
        <FormStatus kind="success" title={t('successTitle', { number: result.number })}>
          {t('successText')}
        </FormStatus>
        <Button size="m" onClick={onClose} className="self-start">
          {t('close')}
        </Button>
      </div>
    );
  }

  return (
    <form noValidate onSubmit={handleSubmit(onSubmit)} onFocusCapture={onFocusCapture} className="relative flex flex-col gap-6" aria-busy={isSubmitting}>
      {/* Товар */}
      <div className="rounded-field bg-surface p-4">
        <p className="chem-wrap text-body font-medium text-text">{product.name}</p>
        <p className="mt-1 text-small text-text-secondary">
          {product.brand.name} · {numberLabel} <span className="tabular-nums text-text">{product.catalogNumber}</span>
          {product.cas ? (
            <>
              {' '}
              · CAS <span className="tabular-nums text-text">{product.cas}</span>
            </>
          ) : null}
        </p>
      </div>

      {/* Фасовка и количество */}
      <div className="grid gap-4 sm:grid-cols-[1fr_auto] sm:items-end">
        {showPackagingSelect ? (
          <Controller
            control={control}
            name="packagingId"
            render={({ field }) => <PackagingSelect product={product} value={field.value} onChange={field.onChange} withCustom />}
          />
        ) : (
          <div className="flex flex-col gap-1.5">
            <span className="text-small text-text-secondary">{tp('packaging')}</span>
            <span className="flex h-12 items-center text-lg text-text">{product.packagings[0]?.label}</span>
          </div>
        )}
        <Controller
          control={control}
          name="quantity"
          render={({ field }) => (
            <QuantityStepper
              label={t('quantity')}
              value={field.value}
              onChange={field.onChange}
              decreaseLabel={t('decrease')}
              increaseLabel={t('increase')}
            />
          )}
        />
      </div>

      {isCustom ? (
        <div className="grid grid-cols-[1fr_auto] gap-3">
          <Input
            label={t('amount')}
            required
            inputMode="decimal"
            autoComplete="off"
            error={err(errors.customAmount?.message)}
            {...register('customAmount')}
          />
          <Select
            label={t('unit')}
            options={UNITS.map((u) => ({ value: u, label: t(`units.${u}`) }))}
            className="w-28"
            {...register('customUnit')}
          />
        </div>
      ) : null}

      <Controller
        control={control}
        name="analogue"
        render={({ field }) => <AnalogueChoice name="one-click-analogue" value={field.value} onChange={field.onChange} />}
      />

      {/* Контакты */}
      <fieldset className="flex flex-col gap-4">
        <legend className="mb-3 text-body font-medium text-text">{t('contacts')}</legend>
        <div className="grid gap-4 md:grid-cols-2">
          <Input label={tf('name')} required autoComplete="name" error={err(errors.name?.message)} {...register('name')} />
          <Input label={tf('companyShort')} required autoComplete="organization" error={err(errors.company?.message)} {...register('company')} />
          <Controller
            control={control}
            name="phone"
            render={({ field }) => (
              <PhoneInput
                label={tf('phone')}
                required
                placeholder={tf('phonePlaceholder')}
                error={err(errors.phone?.message)}
                name={field.name}
                value={field.value}
                onChange={field.onChange}
                onBlur={field.onBlur}
                ref={field.ref}
              />
            )}
          />
          <Input
            label={tf('email')}
            required
            type="email"
            inputMode="email"
            autoComplete="email"
            placeholder={tf('emailPlaceholder')}
            error={err(errors.email?.message)}
            {...register('email')}
          />
        </div>
      </fieldset>

      <ConsentCheckbox kind="personalData" docs={docs} error={err(errors.consent?.message)} {...register('consent')} />
      <Honeypot {...register('website')} />

      {failed ? <FormStatus kind="error" title={tf('errorTitle')}>{tf('errorText')}</FormStatus> : null}

      <div className="flex flex-col gap-3">
        <Button type="submit" size="l" aria-disabled={isSubmitting || undefined}>
          {isSubmitting ? tf('sending') : t('submit')}
        </Button>
        <p className="text-small text-text-secondary">{t('note')}</p>
      </div>
    </form>
  );
}
