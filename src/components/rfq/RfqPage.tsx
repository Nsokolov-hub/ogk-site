'use client';

import { useEffect, useState } from 'react';
import { Controller, useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { CircleCheck, ListPlus, Plus } from 'lucide-react';
import { useLocale, useTranslations } from 'next-intl';
import { z } from 'zod';
import type { SiteRequestItem } from '@/types/requests';
import type { SiteSettings } from '@/types/settings';
import { ConsentCheckbox } from '@/components/forms/ConsentCheckbox';
import { FormStatus } from '@/components/forms/FormStatus';
import { Honeypot } from '@/components/forms/Honeypot';
import { PhoneInput } from '@/components/forms/PhoneInput';
import { SearchBox } from '@/components/search/SearchBox';
import { Button } from '@/components/ui/Button';
import { Checkbox } from '@/components/ui/Checkbox';
import { FileInput } from '@/components/ui/FileInput';
import { Input } from '@/components/ui/Input';
import { Textarea } from '@/components/ui/Textarea';
import { Link } from '@/i18n/navigation';
import { submitSiteRequest } from '@/lib/api';
import { submitErrorKey } from '@/lib/submit-error';
import { track } from '@/lib/analytics';
import { useFormMeta } from '@/lib/hooks';
import { toE164 } from '@/lib/phone';
import { type RfqItem, useRfqStore } from '@/lib/rfq-store';
import { absoluteUrl } from '@/lib/seo';
import { ATTACHMENT_EXTENSIONS, checkAttachment, fields, isValidInn } from '@/lib/validation';
import { BulkAdd } from './BulkAdd';
import { RfqItemRow } from './RfqItemRow';

const schema = z.object({
  name: fields.shortName,
  company: fields.company,
  phone: fields.phone,
  email: fields.email,
  inn: z
    .string()
    .trim()
    .refine((v) => !v || isValidInn(v), 'inn'),
  city: z.string().trim(),
  date: z.string().trim(),
  comment: z.string().trim(),
  consent: fields.consent,
  marketing: z.boolean(),
  website: fields.website,
});
type Values = z.infer<typeof schema>;

/**
 * Корзина запроса /rfq/ (ТЗ 7): позиции, загрузка списка, свободные строки, «аналоги для всех»,
 * форма отправки (RFQ-03) и страница «Спасибо» с номером и составом (RFQ-05).
 */
export function RfqPage({ docs }: { docs: SiteSettings['docs'] }) {
  const t = useTranslations('rfq');
  const tf = useTranslations('form');
  const te = useTranslations('errors');
  const locale = useLocale() as 'ru' | 'en';
  const items = useRfqStore((s) => s.items);
  const hydrated = useRfqStore((s) => s.hydrated);
  const { addFree, setAllAnalogue, clear } = useRfqStore.getState();
  const [showBulk, setShowBulk] = useState(false);

  // /rfq/#bulk (из панели корзины и пустой выдачи) сразу открывает загрузку списка
  useEffect(() => {
    const sync = () => {
      if (window.location.hash === '#bulk') setShowBulk(true);
    };
    sync();
    window.addEventListener('hashchange', sync);
    return () => window.removeEventListener('hashchange', sync);
  }, []);

  useEffect(() => {
    if (hydrated && showBulk && window.location.hash === '#bulk') {
      document.getElementById('rfq-bulk')?.scrollIntoView({ block: 'start' });
    }
  }, [hydrated, showBulk]);
  const [file, setFile] = useState<File | undefined>();
  const [fileError, setFileError] = useState<string | undefined>();
  const [failed, setFailed] = useState<string | null>(null);
  const [done, setDone] = useState<{ number: string; items: RfqItem[] } | null>(null);
  const { onFocusCapture, elapsedMs } = useFormMeta('rfq');

  const allAnalogues = items.length > 0 && items.every((i) => i.analogue === 'allowed');
  const freeInvalid = items.some((i) => i.free && !i.name.trim());

  const {
    register,
    control,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<Values>({
    resolver: zodResolver(schema),
    mode: 'onTouched',
    defaultValues: { name: '', company: '', phone: '', email: '', inn: '', city: '', date: '', comment: '', consent: false, marketing: false, website: '' },
  });
  const err = (key?: string) => (key ? te(key) : undefined);

  const onSubmit = async (v: Values) => {
    if (!items.length || freeInvalid) return;
    setFailed(null);
    const payloadItems: SiteRequestItem[] = items.map((i) => ({
      siteProductId: i.free ? undefined : i.productId,
      brand: i.brand || undefined,
      catalogNumber: i.catalogNumber || undefined,
      cas: i.cas,
      name: i.name.trim(),
      packaging: i.packagingLabel,
      quantity: i.quantity,
      unit: 'pack',
      analogue: i.analogue,
      customPackaging: !!i.customPackaging || (!i.free && i.packagingId === null),
      comment: i.comment?.trim() || undefined,
      pageUrl: i.free ? undefined : absoluteUrl(locale, `/product/${i.slug}/`),
    }));
    try {
      const res = v.website
        ? { number: '—', siteRequestId: '' }
        : await submitSiteRequest({
            kind: 'product_rfq',
            lang: locale,
            customer: {
              name: v.name.trim(),
              company: v.company.trim(),
              phone: toE164(v.phone) ?? v.phone,
              email: v.email.trim(),
              inn: v.inn || undefined,
              city: v.city || undefined,
              comment: v.comment.trim() || undefined,
              marketingConsent: v.marketing,
            },
            items: payloadItems,
            attachment: file,
            personalDataConsent: true,
            antispam: { website: v.website ?? '', elapsedMs: elapsedMs() },
            pageUrl: window.location.href,
            formType: 'rfq',
            desiredDate: v.date || undefined,
          });
      track('quote_request', { items: items.length, brands: Array.from(new Set(items.map((i) => i.brand).filter(Boolean))) });
      track('form_submit', { form_type: 'rfq', page: window.location.pathname });
      setDone({ number: res.number, items });
      clear();
      window.scrollTo({ top: 0, behavior: 'smooth' });
    } catch (error) {
      setFailed(submitErrorKey(error));
    }
  };

  // Страница «Спасибо» (RFQ-05): номер, состав, срок ответа
  if (done) {
    return (
      <section aria-labelledby="rfq-done" className="mt-10 rounded-block bg-surface p-6 md:p-10 lg:p-14">
        <CircleCheck aria-hidden size={48} strokeWidth={1.25} className="text-accent" />
        <h2 id="rfq-done" className="mt-6 text-h2 font-medium text-text">
          {t('done.title', { number: done.number })}
        </h2>
        <p className="mt-4 max-w-[60ch] text-lead text-text">{t('done.text')}</p>
        <h3 className="mt-10 text-h4 font-medium text-text">{t('done.items', { count: done.items.length })}</h3>
        <ol className="mt-4 flex max-w-[880px] flex-col gap-2">
          {done.items.map((i) => (
            <li key={i.key} className="flex flex-wrap items-baseline justify-between gap-x-6 gap-y-1 rounded-field bg-surface-strong px-4 py-3">
              <span className="chem-wrap min-w-0 text-body text-text">
                {i.name}
                <span className="block text-small text-text-secondary">
                  {[i.brand, i.catalogNumber, i.cas ? `CAS ${i.cas}` : ''].filter(Boolean).join(' · ')}
                </span>
              </span>
              <span className="text-small tabular-nums text-text">
                {[i.packagingLabel, t('done.qty', { n: i.quantity })].filter(Boolean).join(' × ')}
              </span>
            </li>
          ))}
        </ol>
        <div className="mt-10 flex flex-wrap gap-3">
          <Button href="/catalog/" size="m">
            {t('done.catalog')}
          </Button>
          <Button href="/" variant="secondary" size="m">
            {t('done.home')}
          </Button>
        </div>
      </section>
    );
  }

  if (!hydrated) {
    return <div aria-hidden className="mt-10 h-64 animate-pulse rounded-block bg-surface" /* taste-skill-ignore: скелетон на долю секунды, пока корзина восстанавливается */ />;
  }

  return (
    <div className="mt-10 flex flex-col gap-10 lg:gap-14">
      {/* Действия над списком */}
      <div className="flex flex-wrap items-center gap-3">
        <Button
          variant={showBulk ? 'primary' : 'secondary'}
          size="m"
          aria-expanded={showBulk}
          aria-controls="rfq-bulk"
          onClick={() => setShowBulk((v) => !v)}
          iconStart={<ListPlus aria-hidden size={20} strokeWidth={1.5} />}
        >
          {t('actions.bulk')}
        </Button>
        <Button variant="secondary" size="m" onClick={() => addFree({ name: '' })} iconStart={<Plus aria-hidden size={20} strokeWidth={1.5} />}>
          {t('actions.free')}
        </Button>
        {items.length ? (
          <Button href="#rfq-form" variant="ghost" size="m" className="ml-auto hidden md:inline-flex">
            {t('actions.toForm')}
          </Button>
        ) : null}
      </div>

      {showBulk ? (
        <div id="rfq-bulk" className="scroll-mt-28">
          <BulkAdd onAttach={(f) => setFile(f)} />
        </div>
      ) : null}

      {items.length ? (
        <section aria-labelledby="rfq-items">
          <div className="flex flex-wrap items-center justify-between gap-4">
            <h2 id="rfq-items" className="text-h3 font-medium text-text">
              {t('items', { count: items.length })}
            </h2>
            <Checkbox label={t('allAnalogues')} checked={allAnalogues} onChange={(e) => setAllAnalogue(e.target.checked ? 'allowed' : 'none')} />
          </div>
          <ul className="mt-6 flex flex-col gap-3">
            {items.map((item) => (
              <RfqItemRow key={item.key} item={item} />
            ))}
          </ul>
        </section>
      ) : (
        <section aria-labelledby="rfq-empty" className="rounded-block bg-surface p-6 md:p-10">
          <h2 id="rfq-empty" className="text-h3 font-medium text-text">
            {t('empty.title')}
          </h2>
          <p className="mt-3 max-w-[60ch] text-body text-text-secondary md:text-lg">{t('empty.text')}</p>
          <SearchBox size="lg" place="rfq" requestHref="#rfq-form" className="mt-6 max-w-[720px]" />
          <div className="mt-6 flex flex-wrap gap-3">
            <Button href="/catalog/" size="m">
              {t('empty.catalog')}
            </Button>
            <Button variant="secondary" size="m" onClick={() => setShowBulk(true)}>
              {t('actions.bulk')}
            </Button>
          </div>
        </section>
      )}

      {/* Форма отправки (RFQ-03) */}
      <section id="rfq-form" aria-labelledby="rfq-form-title" className="scroll-mt-28 rounded-block bg-surface p-6 md:p-10 lg:p-14">
        <div className="grid gap-10 lg:grid-cols-[minmax(0,4fr)_minmax(0,7fr)] lg:gap-16">
          <div>
            <h2 id="rfq-form-title" className="text-h3 font-medium text-text">
              {t('form.title')}
            </h2>
            <p className="mt-4 text-body text-text-secondary md:text-lg">{t('form.text')}</p>
            {items.length ? (
              <p className="mt-6 text-body text-text">{t('form.summary', { count: items.length })}</p>
            ) : null}
          </div>

          <form noValidate onSubmit={handleSubmit(onSubmit)} onFocusCapture={onFocusCapture} className="relative flex flex-col gap-5" aria-busy={isSubmitting}>
            <p className="text-small text-text-secondary">{tf('requiredHint')}</p>
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
              <Input label={t('form.inn')} inputMode="numeric" autoComplete="off" hint={t('form.innHint')} error={err(errors.inn?.message)} {...register('inn')} />
              <Input label={t('form.city')} autoComplete="address-level2" {...register('city')} />
              <Input label={t('form.date')} type="date" {...register('date')} />
            </div>
            <Textarea label={t('form.comment')} rows={3} placeholder={t('form.commentPlaceholder')} {...register('comment')} />
            <FileInput
              label={t('form.attach')}
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
            <Checkbox label={tf('consentMarketing')} {...register('marketing')} />
            <Honeypot {...register('website')} />

            {!items.length ? <p className="text-small text-warning">{t('form.noItems')}</p> : null}
            {freeInvalid ? <p className="text-small text-warning">{t('form.freeInvalid')}</p> : null}
            {failed ? <FormStatus kind="error" title={tf('errorTitle')}>{tf(failed)}</FormStatus> : null}

            <Button type="submit" size="l" aria-disabled={isSubmitting || !items.length || freeInvalid || undefined} className="mt-2">
              {isSubmitting ? tf('sending') : t('form.submit')}
            </Button>
            <p className="text-small text-text-secondary">
              {t('form.note')}{' '}
              <Link href="/delivery/" className="text-accent underline-offset-2 hover:underline">
                {t('form.terms')}
              </Link>
            </p>
          </form>
        </div>
      </section>
    </div>
  );
}
