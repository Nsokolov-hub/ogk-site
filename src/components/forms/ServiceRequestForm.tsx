'use client';

import { useState } from 'react';
import { Controller, useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { Check } from 'lucide-react';
import { useLocale, useTranslations } from 'next-intl';
import { z } from 'zod';
import type { ServiceFieldKind } from '@/types/content';
import type { SiteSettings } from '@/types/settings';
import { Button } from '@/components/ui/Button';
import { Checkbox } from '@/components/ui/Checkbox';
import { FileInput } from '@/components/ui/FileInput';
import { Input } from '@/components/ui/Input';
import { Select } from '@/components/ui/Select';
import { Textarea } from '@/components/ui/Textarea';
import { submitSiteRequest } from '@/lib/api';
import { submitErrorKey } from '@/lib/submit-error';
import { track } from '@/lib/analytics';
import { cn } from '@/lib/cn';
import { useFormMeta } from '@/lib/hooks';
import { toE164 } from '@/lib/phone';
import { ATTACHMENT_EXTENSIONS, checkAttachment, fields } from '@/lib/validation';
import { ConsentCheckbox } from './ConsentCheckbox';
import { FormStatus } from './FormStatus';
import { Honeypot } from './Honeypot';
import { PhoneInput } from './PhoneInput';

const TEMPERATURES = ['15-25', '2-8', '-20', 'dry-ice', 'unknown'] as const;
const REGULATORS = ['minzdrav', 'fstec', 'unknown'] as const;

/**
 * Форма заявки на услугу (SC-06, RFQ-08): набор полей задаётся на услугу, заявка уходит с kind = service.
 * Например, «Холодовая цепь»: откуда, куда, температурный режим, вес, срок.
 */
export function ServiceRequestForm({
  service,
  fieldKinds,
  docs,
}: {
  service: { slug: string; name: string };
  fieldKinds: ServiceFieldKind[];
  docs: SiteSettings['docs'];
}) {
  const t = useTranslations('serviceForm');
  const tf = useTranslations('form');
  const te = useTranslations('errors');
  const locale = useLocale() as 'ru' | 'en';
  const { onFocusCapture, elapsedMs } = useFormMeta(`service_${service.slug}`);
  const [file, setFile] = useState<File | undefined>();
  const [fileError, setFileError] = useState<string | undefined>();
  const [status, setStatus] = useState<{ kind: 'success'; number: string } | { kind: 'error'; key: string } | null>(null);
  const has = (k: ServiceFieldKind) => fieldKinds.includes(k);

  const required = z.string().trim().min(1, 'required');
  const optional = z.string().trim();
  const schema = z.object({
    from: has('route') ? required : optional,
    to: has('route') ? required : optional,
    temperature: optional,
    weight: optional,
    places: optional,
    date: optional,
    goods: has('goods') ? z.string().trim().min(1, 'required').min(10, 'messageShort') : optional,
    permit: z.boolean(),
    regulator: optional,
    name: fields.fullName,
    company: fields.company,
    email: fields.email,
    phone: fields.phone,
    comment: optional,
    consent: fields.consent,
    website: fields.website,
  });
  type Values = z.infer<typeof schema>;

  const empty: Values = {
    from: '',
    to: '',
    temperature: has('temperature') ? '2-8' : '',
    weight: '',
    places: '',
    date: '',
    goods: '',
    permit: false,
    regulator: has('regulator') ? 'unknown' : '',
    name: '',
    company: '',
    email: '',
    phone: '',
    comment: '',
    consent: false,
    website: '',
  };

  const {
    register,
    control,
    handleSubmit,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<Values>({ resolver: zodResolver(schema), mode: 'onTouched', defaultValues: empty });

  const err = (key?: string) => (key ? te(key) : undefined);

  const onSubmit = async (v: Values) => {
    setStatus(null);
    // Поля услуги — отдельным объектом для CRM и строкой в комментарии, чтобы менеджер видел всё сразу
    const serviceFields: Record<string, string> = {};
    if (has('route')) Object.assign(serviceFields, { from: v.from, to: v.to });
    if (has('temperature') && v.temperature) serviceFields.temperature = t(`temperatures.${v.temperature}`);
    if (has('cargo')) Object.assign(serviceFields, { weight: v.weight, places: v.places });
    if (has('date') && v.date) serviceFields.date = v.date;
    if (has('goods')) serviceFields.goods = v.goods;
    if (has('permit')) serviceFields.permit = v.permit ? t('yes') : t('no');
    if (has('regulator') && v.regulator) serviceFields.regulator = t(`regulators.${v.regulator}`);
    const summary = Object.entries(serviceFields)
      .filter(([, val]) => val)
      .map(([k, val]) => `${t(`labels.${k}`)}: ${val}`)
      .join('\n');

    try {
      const res = v.website
        ? { number: '—', siteRequestId: '' }
        : await submitSiteRequest({
            kind: 'service',
            lang: locale,
            customer: {
              name: v.name.trim(),
              company: v.company.trim(),
              phone: toE164(v.phone) ?? v.phone,
              email: v.email.trim(),
              comment: [summary, v.comment.trim()].filter(Boolean).join('\n\n'),
              marketingConsent: false,
            },
            items: [{ name: service.name, quantity: 1, unit: 'pack', analogue: 'none', customPackaging: false, comment: summary }],
            // Поля услуги — с подписями, как их видит клиент: так их прочитает менеджер в CRM
            service: {
              slug: service.slug,
              name: service.name,
              fields: Object.fromEntries(Object.entries(serviceFields).filter(([, val]) => val).map(([k, val]) => [t(`labels.${k}`), val])),
            },
            attachment: file,
            personalDataConsent: true,
            antispam: { website: v.website ?? '', elapsedMs: elapsedMs() },
            pageUrl: window.location.href,
            formType: 'service',
          });
      track('form_submit', { form_type: 'service', service: service.slug, page: window.location.pathname });
      setStatus({ kind: 'success', number: res.number });
      reset(empty);
      setFile(undefined);
    } catch (error) {
      setStatus({ kind: 'error', key: submitErrorKey(error) });
    }
  };

  if (status?.kind === 'success') {
    return (
      <div className="flex flex-col items-start gap-6">
        <FormStatus kind="success" title={tf('successTitle', { number: status.number })}>
          {tf('successText')}
        </FormStatus>
        <Button variant="menu" size="m" onClick={() => setStatus(null)}>
          {tf('newRequest')}
        </Button>
      </div>
    );
  }

  return (
    <form noValidate onSubmit={handleSubmit(onSubmit)} onFocusCapture={onFocusCapture} className="relative flex flex-col gap-5" aria-busy={isSubmitting}>
      <p className="text-small text-text-secondary">{tf('requiredHint')}</p>

      {has('route') ? (
        <div className="grid gap-4 md:grid-cols-2">
          <Input label={t('labels.from')} required placeholder={t('fromPlaceholder')} autoComplete="off" error={err(errors.from?.message)} {...register('from')} />
          <Input label={t('labels.to')} required placeholder={t('toPlaceholder')} autoComplete="off" error={err(errors.to?.message)} {...register('to')} />
        </div>
      ) : null}

      {has('temperature') ? (
        <Controller
          control={control}
          name="temperature"
          render={({ field }) => (
            <fieldset>
              <legend className="mb-2 text-small text-text-secondary">{t('labels.temperature')}</legend>
              <div className="flex flex-wrap gap-2">
                {TEMPERATURES.map((v) => {
                  const checked = field.value === v;
                  return (
                    <label
                      key={v}
                      className={cn(
                        'inline-flex min-h-11 cursor-pointer items-center gap-2 rounded-pill px-4 text-body transition-colors',
                        'has-[:focus-visible]:outline-2 has-[:focus-visible]:outline-offset-2 has-[:focus-visible]:outline-accent',
                        checked ? 'bg-accent text-text-on-accent' : 'bg-surface-strong text-text hover:text-accent',
                      )}
                    >
                      <input type="radio" name={field.name} value={v} checked={checked} onChange={() => field.onChange(v)} className="sr-only" />
                      {checked ? <Check aria-hidden size={16} strokeWidth={2} /> : null}
                      {t(`temperatures.${v}`)}
                    </label>
                  );
                })}
              </div>
            </fieldset>
          )}
        />
      ) : null}

      {has('cargo') ? (
        <div className="grid gap-4 md:grid-cols-2">
          <Input label={t('labels.weight')} inputMode="decimal" autoComplete="off" placeholder={t('weightPlaceholder')} {...register('weight')} />
          <Input label={t('labels.places')} autoComplete="off" placeholder={t('placesPlaceholder')} {...register('places')} />
        </div>
      ) : null}

      {has('regulator') ? (
        <Select
          label={t('labels.regulator')}
          options={REGULATORS.map((r) => ({ value: r, label: t(`regulators.${r}`) }))}
          {...register('regulator')}
        />
      ) : null}

      {has('goods') ? (
        <Textarea label={t('labels.goods')} required placeholder={t('goodsPlaceholder')} error={err(errors.goods?.message)} {...register('goods')} />
      ) : null}

      {has('date') ? <Input label={t('labels.date')} type="date" className="md:max-w-[50%]" {...register('date')} /> : null}

      {has('permit') ? <Checkbox label={t('permitLabel')} {...register('permit')} /> : null}

      <fieldset className="mt-2 flex flex-col gap-4">
        <legend className="mb-3 text-body font-medium text-text">{t('contacts')}</legend>
        <div className="grid gap-4 md:grid-cols-2">
          <Input label={tf('fullName')} required autoComplete="name" error={err(errors.name?.message)} {...register('name')} />
          <Input label={tf('company')} required autoComplete="organization" error={err(errors.company?.message)} {...register('company')} />
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
        </div>
      </fieldset>

      <Textarea label={t('labels.comment')} rows={3} {...register('comment')} />
      <FileInput
        label={t('attach')}
        hint={tf('attachHint')}
        removeLabel={tf('attachRemove')}
        accept={ATTACHMENT_EXTENSIONS.join(',')}
        file={file}
        error={fileError}
        onChange={(f) => {
          if (!f) {
            setFile(undefined);
            setFileError(undefined);
            return;
          }
          const problem = checkAttachment(f);
          setFileError(problem ? te(problem) : undefined);
          setFile(problem ? undefined : f);
        }}
      />
      <ConsentCheckbox kind="personalData" docs={docs} error={err(errors.consent?.message)} {...register('consent')} />
      <Honeypot {...register('website')} />

      {status?.kind === 'error' ? <FormStatus kind="error" title={tf('errorTitle')}>{tf(status.key)}</FormStatus> : null}

      <Button type="submit" size="l" aria-disabled={isSubmitting || undefined} className="mt-2">
        {isSubmitting ? tf('sending') : t('submit')}
      </Button>
      <p className="text-small text-text-secondary">{t('note')}</p>
    </form>
  );
}
