'use client';

import { useTranslations } from 'next-intl';
import type { ProductPreview } from '@/types/catalog';
import { AddToRfqButton } from '@/components/product/AddToRfqButton';
import { Link } from '@/i18n/navigation';
import { cn } from '@/lib/cn';

/** Режим таблицы для профессионалов (ТЗ 5.3): кат. №, название, CAS, бренд, фасовка */
export function ProductTable({ items, caption }: { items: ProductPreview[]; caption: string }) {
  const t = useTranslations('catalog.table');
  const tp = useTranslations('product');
  const th = 'px-4 py-3 text-left text-small font-medium text-text-secondary';
  const td = 'px-4 py-3 align-middle';

  return (
    <>
      {/* Телефон: строки списком, без боковой прокрутки */}
      <ul className="flex flex-col gap-2 lg:hidden">
        {items.map((p) => (
          <li key={p.id} className="rounded-field bg-surface p-4">
            <Link href={`/product/${p.slug}/`} title={p.name} className="chem-wrap line-clamp-2 text-body font-medium text-text transition-colors hover:text-accent">
              {p.name}
            </Link>
            <p className="mt-1 flex flex-wrap gap-x-3 text-small text-text-secondary">
              <span>{p.brand.name}</span>
              <span className="tabular-nums">{p.catalogNumber}</span>
              {p.cas ? <span className="tabular-nums">CAS {p.cas}</span> : null}
            </p>
            <p className="mt-1 text-small text-text">
              {p.packagings.map((pk) => pk.label).join(' / ')}
              {p.customPackaging ? <span className="text-accent"> · {tp('anyPackaging')}</span> : null}
            </p>
            <div className="mt-3">
              <AddToRfqButton product={p} packagingId={p.packagings[0]?.id ?? null} place="list" />
            </div>
          </li>
        ))}
      </ul>
      <div className="relative hidden overflow-x-auto rounded-block border border-border lg:block">
        <table className="w-full min-w-[760px] border-collapse text-small">
          <caption className="sr-only">{caption}</caption>
          <thead className="bg-surface-strong">
            <tr>
              <th scope="col" className={th}>{t('catalogNumber')}</th>
              <th scope="col" className={th}>{t('name')}</th>
              <th scope="col" className={th}>{t('cas')}</th>
              <th scope="col" className={th}>{t('brand')}</th>
              <th scope="col" className={th}>{t('packaging')}</th>
              <th scope="col" className={cn(th, 'w-[150px]')}>
                <span className="sr-only">{t('actions')}</span>
              </th>
            </tr>
          </thead>
          <tbody>
            {items.map((p, i) => (
              <tr key={p.id} className={cn('border-t border-border', i % 2 === 1 && 'bg-surface')} /* taste-skill-ignore: строки настоящей таблицы */>
                <td className={cn(td, 'whitespace-nowrap tabular-nums text-text')}>{p.catalogNumber}</td>
                <td className={cn(td, 'max-w-[360px]')}>
                  <Link href={`/product/${p.slug}/`} title={p.name} className="chem-wrap line-clamp-2 font-medium text-text transition-colors hover:text-accent">
                    {p.name}
                  </Link>
                </td>
                <td className={cn(td, 'whitespace-nowrap tabular-nums text-text')}>{p.cas ?? '—'}</td>
                <td className={cn(td, 'text-text')}>{p.brand.name}</td>
                <td className={cn(td, 'text-text')}>
                  {p.packagings.map((pk) => pk.label).join(' / ')}
                  {p.customPackaging ? <span className="block text-caption text-accent">{tp('anyPackaging')}</span> : null}
                </td>
                <td className={td}>
                  <AddToRfqButton product={p} packagingId={p.packagings[0]?.id ?? null} place="list" className="w-[136px] px-3 sm:px-3" />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </>
  );
}
