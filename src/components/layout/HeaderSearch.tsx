'use client';

import { useRef, useState } from 'react';
import { Search } from 'lucide-react';
import { useLocale, useTranslations } from 'next-intl';
import { routing } from '@/i18n/routing';
import { cn } from '@/lib/cn';
import { useFieldIds } from '@/components/ui/Field';

/**
 * Строка поиска (SRCH-01). Обычная GET-форма на /search/ — работает и без JS.
 * Подсказки после 2 символов подключим отдельной задачей.
 */
export function HeaderSearch({ autoFocus, className }: { autoFocus?: boolean; className?: string }) {
  const t = useTranslations('search');
  const locale = useLocale();
  const { fieldId } = useFieldIds();
  const [query, setQuery] = useState('');
  const inputRef = useRef<HTMLInputElement>(null);
  const action = locale === routing.defaultLocale ? '/search/' : `/${locale}/search/`;

  return (
    <form
      role="search"
      action={action}
      method="get"
      className={cn('relative w-full', className)}
      onSubmit={(e) => {
        if (!query.trim()) {
          e.preventDefault();
          inputRef.current?.focus();
        }
      }}
    >
      <label htmlFor={fieldId} className="sr-only">
        {t('label')}
      </label>
      <Search aria-hidden size={18} strokeWidth={1.5} className="pointer-events-none absolute left-4 top-1/2 -translate-y-1/2 text-text-secondary" />
      <input
        ref={inputRef}
        id={fieldId}
        type="search"
        name="q"
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        autoComplete="off"
        autoFocus={autoFocus}
        enterKeyHint="search"
        spellCheck={false}
        placeholder={t('placeholder')}
        className="h-11 w-full rounded-pill border border-border bg-base/50 pl-11 pr-[5.5rem] text-body text-text outline-offset-0 transition-colors placeholder:text-text-placeholder hover:border-text-secondary focus-visible:border-accent"
      />
      <button
        type="submit"
        className="absolute right-1 top-1 h-9 rounded-pill bg-accent px-4 text-small font-medium text-text-on-accent transition-colors hover:bg-accent-hover"
      >
        {t('submit')}
      </button>
      {/* SearchSuggest: подсказки по товарам, субстанциям, категориям и брендам (SRCH-01) */}
    </form>
  );
}
