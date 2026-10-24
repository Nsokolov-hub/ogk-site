'use client';

import { useEffect, useRef, useState } from 'react';
import { Controller, useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { useLocale, useTranslations } from 'next-intl';
import { z } from 'zod';
import { Button } from '@/components/ui/Button';
import { FileInput } from '@/components/ui/FileInput';
import { Input } from '@/components/ui/Input';
import { Textarea } from '@/components/ui/Textarea';
import { submitSiteRequest } from '@/lib/api';
import { submitErrorKey } from '@/lib/submit-error';
import { track } from '@/lib/analytics';
import { useFormMeta } from '@/lib/hooks';
import { toE164 } from '@/lib/phone';
import { ATTACHMENT_EXTENSIONS, checkAttachment, fields } from '@/lib/validation';
import type { SiteSettings } from '@/types/settings';
import { ConsentCheckbox } from './ConsentCheckbox';
import { FormStatus } from './FormStatus';
import { Honeypot } from './Honeypot';
import { PhoneInput } from './PhoneInput';

const schema = z.object({
  name: fields.fullName,
  company: fields.company,
  email: fields.email,
  phone: fields.phone,
  message: fields.message,
  consent: fields.consent,
  website: fields.website,
});

type Values = z.infer<typeof schema>;

/** Событие «подставить текст в форму заявки» — кнопки «Запросить CoA партии», «Запросить SDS» на карточке */
export const REQUEST_PREFILL_EVENT = 'ogk:request-prefill';

export function prefillRequest(text: string) {
  window.dispatchEvent(new CustomEvent<string>(REQUEST_PREFILL_EVENT, { detail: text }));
}

/**
 * Форма «Отправьте ваш запрос»: главная, категории, карточки, бренды, страницы доверия. Заявка kind = general.
 * defaultMessage — подставленный запрос (товар с карточки, текст из пустого поиска, SC-03).
 */
export function RequestForm({
  docs,
  defaultMessage = '',
  formType = 'request',
}: {
  docs: SiteSettings['docs'];
  defaultMessage?: string;
  formType?: string;
}) {
  const t = useTranslations('form');
  const te = useTranslations('errors');
  const locale = useLocale() as 'ru' | 'en';
  const { onFocusCapture, elapsedMs } = useFormMeta(formType);
  const formRef = useRef<HTMLFormElement>(null);
  const [file, setFile] = useState<File | undefined>();
  const [fileError, setFileError] = useState<string | undefined>();
  const [status, setStatus] = useState<{ kind: 'success'; number: string } | { kind: 'error'; key: string } | null>(null);

  const {
    register,
    control,
    handleSubmit,
    reset,
    getValues,
    setValue,
    formState: { errors, isSubmitting },
  } = useForm<Values>({
    resolver: zodResolver(schema),
    mode: 'onTouched',
    defaultValues: { name: '', company: '', email: '', phone: '', message: defaultMessage, consent: false, website: '' },
  });

  // Кнопки «Запросить документ» дописывают строку в запрос, прокручивают к форме и ставят фокус в поле
  useEffect(() => {
    const onPrefill = (e: Event) => {
      const text = (e as CustomEvent<string>).detail;
      const current = getValues('message').trim();
      setValue('message', current && !current.includes(text) ? `${current}\n${text}` : current || text, { shouldDirty: true });
      setStatus(null);
      const el = formRef.current;
      if (!el) return;
      el.scrollIntoView({ behavior: 'smooth', block: 'start' });
      el.querySelector<HTMLTextAreaElement>('textarea')?.focus({ preventScroll: true });
    };
    window.addEventListener(REQUEST_PREFILL_EVENT, onPrefill);
    return () => window.removeEventListener(REQUEST_PREFILL_EVENT, onPrefill);
  }, [getValues, setValue]);

  const err = (key?: string) => (key ? te(key) : undefined);

  const onSubmit = async (v: Values) => {
    setStatus(null);
    try {
      const res = v.website
        ? { number: '—', siteRequestId: '' } // бот: делаем вид, что всё хорошо, и ничего не отправляем
        : await submitSiteRequest({
            kind: 'general',
            lang: locale,
            customer: {
              name: v.name.trim(),
              company: v.company.trim(),
              phone: toE164(v.phone) ?? v.phone,
              email: v.email.trim(),
              comment: v.message.trim(),
              marketingConsent: false,
            },
            items: [],
            attachment: file,
            personalDataConsent: true,
            antispam: { website: v.website ?? '', elapsedMs: elapsedMs() },
            pageUrl: window.location.href,
            formType,
          });
      track('form_submit', { form_type: formType, page: window.location.pathname });
      setStatus({ kind: 'success', number: res.number });
      reset({ name: '', company: '', email: '', phone: '', message: defaultMessage, consent: false, website: '' });
      setFile(undefined);
    } catch (error) {
      setStatus({ kind: 'error', key: submitErrorKey(error) });
    }
  };

  if (status?.kind === 'success') {
    return (
      <div className="flex flex-col items-start gap-6">
        <FormStatus kind="success" title={t('successTitle', { number: status.number })}>
          {t('successText')}
        </FormStatus>
        <Button variant="menu" size="m" onClick={() => setStatus(null)}>
          {t('newRequest')}
        </Button>
      </div>
    );
  }

  return (
    <form
      ref={formRef}
      noValidate
      onSubmit={handleSubmit(onSubmit)}
      onFocusCapture={onFocusCapture}
      className="relative flex scroll-mt-32 flex-col gap-4 md:gap-5"
      aria-busy={isSubmitting}
    >
      <p className="text-small text-text-secondary">{t('requiredHint')}</p>
      <div className="grid gap-4 md:grid-cols-2 md:gap-5">
        <Input label={t('fullName')} required autoComplete="name" placeholder={t('fullNamePlaceholder')} error={err(errors.name?.message)} {...register('name')} />
        <Input
          label={t('company')}
          required
          autoComplete="organization"
          placeholder={t('companyPlaceholder')}
          error={err(errors.company?.message)}
          {...register('company')}
        />
        <Input
          label={t('email')}
          required
          type="email"
          inputMode="email"
          autoComplete="email"
          placeholder={t('emailPlaceholder')}
          error={err(errors.email?.message)}
          {...register('email')}
        />
        <Controller
          control={control}
          name="phone"
          render={({ field }) => (
            <PhoneInput
              label={t('phone')}
              required
              placeholder={t('phonePlaceholder')}
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
      <Textarea label={t('message')} required placeholder={t('messagePlaceholder')} error={err(errors.message?.message)} {...register('message')} />
      <FileInput
        label={t('attach')}
        hint={t('attachHint')}
        removeLabel={t('attachRemove')}
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

      {status?.kind === 'error' ? <FormStatus kind="error" title={t('errorTitle')}>{t(status.key)}</FormStatus> : null}

      <Button type="submit" size="l" aria-disabled={isSubmitting || undefined} className="mt-2">
        {isSubmitting ? t('sending') : t('submit')}
      </Button>
    </form>
  );
}
