import { getTranslations } from 'next-intl/server';
import type { SiteSettings } from '@/types/settings';
import { CopyButton } from '@/components/product/detail/CopyButton';
import { cn } from '@/lib/cn';

/** Реквизиты организации — один источник для страниц доверия, подвала и Organization (ADM-10) */
export async function Requisites({ settings, className }: { settings: SiteSettings; className?: string }) {
  const t = await getTranslations('trust.requisites');
  const rows = [
    { label: t('name'), value: settings.legal.name },
    { label: t('inn'), value: settings.legal.inn, copy: true },
    { label: t('kpp'), value: settings.legal.kpp, copy: true },
    { label: t('ogrn'), value: settings.legal.ogrn, copy: true },
    { label: t('address'), value: settings.address.full },
    { label: t('hours'), value: settings.hours },
  ];
  return (
    <dl className={cn('overflow-hidden rounded-field', className)}>
      {rows.map((r, i) => (
        <div key={r.label} className={cn('grid gap-1 px-4 py-3 sm:grid-cols-[12rem_minmax(0,1fr)] sm:gap-6 md:px-5', i % 2 === 0 && 'bg-surface')}>
          <dt className="text-small text-text-secondary sm:text-body">{r.label}</dt>
          <dd className="flex items-center gap-1 text-body tabular-nums text-text">
            <span id={r.copy ? `copy-${r.value}` : undefined}>{r.value}</span>
            {r.copy ? <CopyButton value={r.value} label={r.label} className="size-8" /> : null}
          </dd>
        </div>
      ))}
    </dl>
  );
}
