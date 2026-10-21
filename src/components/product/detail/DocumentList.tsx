'use client';

import { Download, FileText } from 'lucide-react';
import { useTranslations } from 'next-intl';
import type { ProductDocument } from '@/types/catalog';
import { prefillRequest } from '@/components/forms/RequestForm';
import { track } from '@/lib/analytics';

/**
 * Документы карточки (ТЗ 5.4, SC-08): файл — скачать (событие download_document),
 * без файла — «Запросить»: строка попадает в форму заявки внизу страницы.
 * CoA конкретной партии — всегда по запросу.
 */
export function DocumentList({
  documents,
  productLabel,
  sku,
  withBatchCoa,
}: {
  documents: ProductDocument[];
  productLabel: string;
  sku: string;
  withBatchCoa: boolean;
}) {
  const t = useTranslations('productPage.docs');
  const rows = [...documents];
  if (withBatchCoa) rows.push({ type: 'coa', title: t('coaBatch'), lang: 'en' });

  if (!rows.length) return <p className="text-body text-text-secondary">{t('empty')}</p>;

  const action =
    'inline-flex h-10 shrink-0 items-center gap-2 rounded-pill bg-surface-strong px-4 text-small font-medium text-accent transition-colors hover:text-accent-hover';

  return (
    <ul className="flex flex-col gap-2">
      {rows.map((d, i) => {
        const isBatch = withBatchCoa && i === rows.length - 1;
        return (
          <li key={`${d.type}-${d.title}`} className="flex items-center gap-3 rounded-field bg-surface px-4 py-3">
            <FileText aria-hidden size={22} strokeWidth={1.5} className="shrink-0 text-accent" />
            <span className="min-w-0 flex-1 text-small text-text md:text-body">
              {d.title}
              <span className="ml-2 text-caption uppercase text-text-secondary" aria-label={t('lang', { lang: d.lang })}>
                {d.lang}
              </span>
            </span>
            {d.href ? (
              <a
                href={d.href}
                download
                onClick={() => track('download_document', { type: d.type, sku })}
                className={action}
              >
                <Download aria-hidden size={16} strokeWidth={1.5} />
                {t('download')}
              </a>
            ) : (
              <button
                type="button"
                className={action}
                onClick={() => prefillRequest(t('requestText', { doc: d.title, product: productLabel }))}
              >
                {isBatch ? t('requestCoa') : t('request')}
              </button>
            )}
          </li>
        );
      })}
    </ul>
  );
}
