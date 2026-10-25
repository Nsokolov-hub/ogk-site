'use client';

import { useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { useLocale, useTranslations } from 'next-intl';
import { z } from 'zod';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { subscribe } from '@/lib/api';
import { track } from '@/lib/analytics';
import { useFormMeta } from '@/lib/hooks';
import { fields } from '@/lib/validation';
import type { Locale } from '@/i18n/routing';
import type { SiteSettings } from '@/types/settings';
import { ConsentCheckbox } from './ConsentCheckbox';
import { FormStatus } from './FormStatus';
import { Honeypot } from './Honeypot';

const schema = z.object({
  email: fields.email,
  personalData: fields.consent,
  marketing: fields.consent,
  website: fields.website,
});

type Values = z.infer<typeof schema>;

/** Подписка на рассылку: два отдельных обязательных согласия (152-ФЗ и 38-ФЗ) */
export function SubscribeForm({ docs }: { docs: SiteSettings['docs'] }) {
  const t = useTranslations('subscribe');
  const tf = useTranslations('form');
  const te = useTranslations('errors');
  const locale = useLocale() as Locale;
  const { onFocusCapture } = useFormMeta('subscribe');
  const [status, setStatus] = useState<'success' | 'error' | null>(null);

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<Values>({
    resolver: zodResolver(schema),
    mode: 'onTouched',
    defaultValues: { email: '', personalData: false, marketing: false, website: '' },
  });

  const err = (key?: string) => (key ? te(key) : undefined);

  const onSubmit = async (v: Values) => {
    setStatus(null);
    try {
      if (!v.website) {
        await subscribe({
          email: v.email.trim(),
          personalDataConsent: true,
          marketingConsent: true,
          lang: locale,
          source: 'home',
          pageUrl: window.location.href.split('?')[0],
        });
      }
      track('subscribe');
      track('form_submit', { form_type: 'subscribe', page: window.location.pathname });
      setStatus('success');
    } catch {
      setStatus('error');
    }
  };

  if (status === 'success') return <FormStatus kind="success" title={t('success')} />;

  return (
    <form noValidate onSubmit={handleSubmit(onSubmit)} onFocusCapture={onFocusCapture} className="relative flex flex-col gap-4" aria-busy={isSubmitting}>
      <div className="flex flex-col gap-3 md:flex-row md:items-start">
        <Input
          label={t('email')}
          hideLabel
          required
          type="email"
          inputMode="email"
          autoComplete="email"
          placeholder={t('placeholder')}
          error={err(errors.email?.message)}
          className="md:flex-1"
          {...register('email')}
        />
        <Button type="submit" size="m" aria-disabled={isSubmitting || undefined} className="md:mt-0 md:h-[54px]">
          {isSubmitting ? tf('sending') : t('submit')}
        </Button>
      </div>
      <ConsentCheckbox kind="personalData" docs={docs} error={err(errors.personalData?.message)} {...register('personalData')} />
      <ConsentCheckbox kind="marketing" docs={docs} error={err(errors.marketing?.message)} {...register('marketing')} />
      <Honeypot {...register('website')} />
      {status === 'error' ? <FormStatus kind="error" title={tf('errorTitle')}>{tf('errorText')}</FormStatus> : null}
    </form>
  );
}
