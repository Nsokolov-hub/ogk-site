'use client';

import { useEffect, useState } from 'react';
import { Check, Copy } from 'lucide-react';
import { useTranslations } from 'next-intl';
import { cn } from '@/lib/cn';

/** Копирование кат. № или CAS одним нажатием (ТЗ 5.4) */
export function CopyButton({ value, label, className }: { value: string; label: string; className?: string }) {
  const t = useTranslations('productPage');
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    if (!copied) return;
    const id = window.setTimeout(() => setCopied(false), 1800);
    return () => window.clearTimeout(id);
  }, [copied]);

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(value);
      setCopied(true);
    } catch {
      // Буфер обмена недоступен (http, старый браузер) — выделяем текст, чтобы скопировать вручную
      const range = document.createRange();
      const el = document.getElementById(`copy-${value}`);
      if (el) {
        range.selectNodeContents(el);
        window.getSelection()?.removeAllRanges();
        window.getSelection()?.addRange(range);
      }
    }
  };

  return (
    <>
      <button
        type="button"
        onClick={copy}
        aria-label={t('copy', { label })}
        className={cn(
          'inline-grid size-9 shrink-0 place-items-center rounded-full text-text-secondary transition-colors hover:bg-surface-strong hover:text-accent',
          copied && 'text-accent',
          className,
        )}
      >
        {copied ? <Check aria-hidden size={16} strokeWidth={2} /> : <Copy aria-hidden size={16} strokeWidth={1.5} />}
      </button>
      <span role="status" aria-live="polite" className="sr-only">
        {copied ? t('copied', { label }) : ''}
      </span>
    </>
  );
}
