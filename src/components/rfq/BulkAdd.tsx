'use client';

import { useId, useState } from 'react';
import { CircleAlert, CircleCheck, CircleHelp, Upload } from 'lucide-react';
import { useTranslations } from 'next-intl';
import { FormStatus } from '@/components/forms/FormStatus';
import { Button } from '@/components/ui/Button';
import { Select } from '@/components/ui/Select';
import { Textarea } from '@/components/ui/Textarea';
import { track } from '@/lib/analytics';
import { cn } from '@/lib/cn';
import { useRfqStore } from '@/lib/rfq-store';
import type { BatchLineResult } from '@/lib/search';

const SKIP = '__skip__';
const FREE = '__free__';
const MAX_LINES = 200;

/**
 * Запрос по списку (SC-02, SRCH-09): до 200 строк из буфера или файла csv/txt. Каждая строка получает статус:
 * найдено точно / несколько кандидатов (выбор) / не найдено (свободная строка). «Добавить всё в корзину».
 * xlsx без разбора на клиенте прикладываем к заявке — исходный файл уходит в CRM.
 */
export function BulkAdd({ onAttach }: { onAttach: (file: File) => void }) {
  const t = useTranslations('rfq.bulk');
  const uid = useId().replace(/[^a-zA-Z0-9_-]/g, '');
  const [text, setText] = useState('');
  const [results, setResults] = useState<BatchLineResult[] | null>(null);
  const [choice, setChoice] = useState<Record<number, string>>({});
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(false);
  const [note, setNote] = useState<string | null>(null);
  const [added, setAdded] = useState<number | null>(null);
  const add = useRfqStore((s) => s.add);
  const addFree = useRfqStore((s) => s.addFree);

  const lines = text.split(/\r?\n/).map((l) => l.trim()).filter(Boolean);

  const match = async (source: string[]) => {
    setLoading(true);
    setError(false);
    setAdded(null);
    try {
      const res = await fetch('/api/search/batch', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ lines: source.slice(0, MAX_LINES) }),
      });
      if (!res.ok) throw new Error(String(res.status));
      const data = (await res.json()) as { results: BatchLineResult[] };
      setResults(data.results);
      // По умолчанию: точное совпадение — добавить, несколько — первый кандидат, не найдено — свободной строкой
      setChoice(Object.fromEntries(data.results.map((r, i) => [i, r.status === 'none' ? FREE : r.candidates[0].id])));
      track('bulk_upload', { rows: data.results.length, found: data.results.filter((r) => r.status === 'exact').length });
    } catch {
      setError(true);
    } finally {
      setLoading(false);
    }
  };

  const onFile = async (file: File | undefined) => {
    if (!file) return;
    const name = file.name.toLowerCase();
    if (name.endsWith('.csv') || name.endsWith('.txt')) {
      // Колонки CSV склеиваем табуляцией: последняя числовая колонка — количество
      const content = await file.text();
      const rows = content
        .split(/\r?\n/)
        .map((r) => r.split(/[;,\t]/).map((c) => c.replace(/^"|"$/g, '').trim()).filter(Boolean).join('\t'))
        .filter(Boolean);
      setText(rows.join('\n'));
      setNote(t('fileParsed', { name: file.name, count: rows.length }));
      onAttach(file);
      await match(rows);
    } else if (name.endsWith('.xlsx')) {
      onAttach(file);
      setNote(t('xlsxAttached', { name: file.name }));
    } else {
      setNote(t('fileType'));
    }
  };

  const addAll = () => {
    if (!results) return;
    let n = 0;
    results.forEach((r, i) => {
      const c = choice[i];
      if (c === SKIP) return;
      if (c === FREE) {
        addFree({ name: r.query, quantity: r.quantity });
        n += 1;
        return;
      }
      const p = r.candidates.find((x) => x.id === c);
      if (!p) return;
      const pk = p.packagings[0];
      add({
        productId: p.id,
        slug: p.slug,
        name: p.name,
        brand: p.brand.name,
        catalogNumber: p.catalogNumber,
        cas: p.cas,
        categorySlug: p.categorySlug,
        packagings: p.packagings,
        customAllowed: p.customPackaging,
        packagingId: pk?.id ?? null,
        packagingLabel: pk?.label,
        quantity: r.quantity,
        analogue: 'none',
      });
      track('add_to_rfq', { sku: p.catalogNumber, brand: p.brand.name, place: 'list' });
      n += 1;
    });
    setAdded(n);
    setResults(null);
    setText('');
  };

  const stats = results
    ? { exact: results.filter((r) => r.status === 'exact').length, multiple: results.filter((r) => r.status === 'multiple').length, none: results.filter((r) => r.status === 'none').length }
    : null;

  return (
    <div className="rounded-block bg-surface p-5 md:p-8">
      <h2 className="text-h4 font-medium text-text">{t('title')}</h2>
      <p className="mt-2 max-w-[70ch] text-body text-text-secondary">{t('text')}</p>

      <div className="mt-5 grid gap-4">
        <Textarea
          label={t('label')}
          hint={t('hint', { max: MAX_LINES })}
          placeholder={t('placeholder')}
          rows={6}
          value={text}
          onChange={(e) => setText(e.target.value)}
          className="[&_textarea]:font-normal [&_textarea]:tabular-nums"
        />
        <div className="flex flex-wrap items-center gap-3">
          <Button size="m" onClick={() => match(lines)} aria-disabled={loading || !lines.length || undefined} disabled={!lines.length}>
            {loading ? t('loading') : t('match', { count: Math.min(lines.length, MAX_LINES) })}
          </Button>
          <label
            htmlFor={`${uid}-file`}
            className="inline-flex h-12 cursor-pointer items-center gap-2 rounded-pill bg-surface-strong px-[22px] text-body font-semibold text-accent transition-colors hover:text-accent-hover has-[:focus-visible]:outline-2 has-[:focus-visible]:outline-offset-2 has-[:focus-visible]:outline-accent sm:text-lg"
          >
            <Upload aria-hidden size={18} strokeWidth={1.5} />
            {t('file')}
            <input
              id={`${uid}-file`}
              type="file"
              accept=".csv,.txt,.xlsx"
              className="sr-only"
              onChange={(e) => {
                void onFile(e.target.files?.[0]);
                e.target.value = '';
              }}
            />
          </label>
        </div>
        {note ? <p className="text-small text-text-secondary" role="status">{note}</p> : null}
        {error ? <FormStatus kind="error" title={t('errorTitle')}>{t('errorText')}</FormStatus> : null}
        {added !== null ? (
          <FormStatus kind="success" title={t('added', { count: added })} />
        ) : null}
      </div>

      {results && stats ? (
        <div className="mt-8">
          <p className="text-body text-text" role="status">
            {t('stats', { exact: stats.exact, multiple: stats.multiple, none: stats.none })}
          </p>
          <ul className="mt-4 flex flex-col gap-2">
            {results.map((r, i) => {
              const Icon = r.status === 'exact' ? CircleCheck : r.status === 'multiple' ? CircleHelp : CircleAlert;
              return (
                <li key={`${r.line}-${i}`} className="grid gap-3 rounded-field bg-surface-strong p-4 md:grid-cols-[minmax(0,14rem)_minmax(0,1fr)] md:items-center md:gap-6">
                  <div className="flex min-w-0 items-start gap-3">
                    <Icon
                      aria-hidden
                      size={20}
                      strokeWidth={1.5}
                      className={cn('mt-0.5 shrink-0', r.status === 'exact' ? 'text-accent' : r.status === 'multiple' ? 'text-warning' : 'text-text-secondary')}
                    />
                    <div className="min-w-0">
                      <p className="chem-wrap text-body tabular-nums text-text">{r.query}</p>
                      <p className="text-small text-text-secondary">
                        {t(`status.${r.status}`)} · {t('qty', { n: r.quantity })}
                      </p>
                    </div>
                  </div>
                  <Select
                    label={t('choose')}
                    hideLabel
                    options={[
                      ...r.candidates.map((c) => ({
                        value: c.id,
                        label: `${c.brand.name} · ${c.catalogNumber} · ${c.name}${c.cas ? ` · CAS ${c.cas}` : ''}`,
                      })),
                      { value: FREE, label: t('asFree') },
                      { value: SKIP, label: t('skip') },
                    ]}
                    value={choice[i] ?? SKIP}
                    onChange={(e) => setChoice((prev) => ({ ...prev, [i]: e.target.value }))}
                  />
                </li>
              );
            })}
          </ul>
          <div className="mt-6 flex flex-wrap items-center gap-3">
            <Button size="m" onClick={addAll}>
              {t('addAll', { count: Object.values(choice).filter((c) => c !== SKIP).length })}
            </Button>
            <Button variant="ghost" size="m" onClick={() => setResults(null)}>
              {t('cancel')}
            </Button>
          </div>
          <p className="mt-3 text-small text-text-secondary">{t('packagingNote')}</p>
        </div>
      ) : null}
    </div>
  );
}
