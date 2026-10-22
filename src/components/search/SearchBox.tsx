'use client';

import { useEffect, useRef, useState, type KeyboardEvent, type ReactNode } from 'react';
import { Search } from 'lucide-react';
import { useLocale, useTranslations } from 'next-intl';
import { Formula } from '@/components/content/Formula';
import { useFieldIds } from '@/components/ui/Field';
import { Link } from '@/i18n/navigation';
import { routing } from '@/i18n/routing';
import { track } from '@/lib/analytics';
import { cn } from '@/lib/cn';
import { SUGGEST_MIN, type SuggestResult } from '@/lib/search-shared';

/** Подсвечивает совпавшую часть строки */
function Highlight({ text, query }: { text: string; query: string }) {
  const q = query.trim();
  const i = q ? text.toLowerCase().indexOf(q.toLowerCase()) : -1;
  if (i < 0) return <>{text}</>;
  return (
    <>
      {text.slice(0, i)}
      <mark className="bg-transparent text-accent">{text.slice(i, i + q.length)}</mark>
      {text.slice(i + q.length)}
    </>
  );
}

type State = { status: 'idle' } | { status: 'loading' } | { status: 'done'; result: SuggestResult } | { status: 'error' };

/**
 * Строка поиска с подсказками (SRCH-01): после 2 символов — до 6 позиций (точный кат. № или CAS первым),
 * затем группы «Субстанции», «Категории», «Бренды».
 * Без JS работает как обычная GET-форма на /search/. Подсказки — список ссылок:
 * ↓ из поля переходит в список, ↑/↓ — по пунктам, Esc — обратно в поле.
 */
export function SearchBox({
  size = 'md',
  value,
  defaultValue,
  onValueChange,
  autoFocus,
  requestHref = '/rfq/',
  place,
  className,
  inputClassName,
}: {
  size?: 'md' | 'lg';
  value?: string;
  /** Начальное значение, например запрос со страницы результатов */
  defaultValue?: string;
  onValueChange?: (v: string) => void;
  autoFocus?: boolean;
  /** Куда вести из пустой выдачи: на главной — к форме, на остальных страницах — в корзину запроса */
  requestHref?: string;
  /** Для аналитики: header | hero | … */
  place: string;
  className?: string;
  inputClassName?: string;
}) {
  const t = useTranslations('search');
  const locale = useLocale();
  const { fieldId } = useFieldIds();
  const [own, setOwn] = useState(defaultValue ?? '');
  const query = value ?? own;
  const setQuery = (v: string) => (onValueChange ? onValueChange(v) : setOwn(v));
  const [state, setState] = useState<State>({ status: 'idle' });
  const [open, setOpen] = useState(false);
  const rootRef = useRef<HTMLFormElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const listRef = useRef<HTMLUListElement>(null);
  const action = locale === routing.defaultLocale ? '/search/' : `/${locale}/search/`;
  const listId = `${fieldId}-suggest`;
  const lg = size === 'lg';

  // Запрос подсказок с задержкой 180 мс; предыдущий запрос отменяется
  useEffect(() => {
    const q = query.trim();
    if (q.length < SUGGEST_MIN) {
      setState({ status: 'idle' });
      return;
    }
    const ctrl = new AbortController();
    const timer = window.setTimeout(async () => {
      setState({ status: 'loading' });
      try {
        const res = await fetch(`/api/search/suggest/?q=${encodeURIComponent(q)}&lang=${locale}`, { signal: ctrl.signal });
        if (!res.ok) throw new Error(String(res.status));
        const result = (await res.json()) as SuggestResult;
        setState({ status: 'done', result });
        track(result.total ? 'site_search' : 'search_no_results', { query: q, place, results: result.total, mode: 'suggest' });
      } catch (e) {
        if ((e as Error).name !== 'AbortError') setState({ status: 'error' });
      }
    }, 180);
    return () => {
      ctrl.abort();
      window.clearTimeout(timer);
    };
  }, [query, place, locale]);

  // Закрываем по клику вне формы
  useEffect(() => {
    if (!open) return;
    const onPointer = (e: PointerEvent) => {
      if (!rootRef.current?.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener('pointerdown', onPointer);
    return () => document.removeEventListener('pointerdown', onPointer);
  }, [open]);

  const links = () => Array.from(listRef.current?.querySelectorAll<HTMLAnchorElement>('a[data-suggest]') ?? []);

  const onInputKey = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'ArrowDown' && open) {
      const first = links()[0];
      if (first) {
        e.preventDefault();
        first.focus();
      }
    }
    if (e.key === 'Escape') setOpen(false);
  };

  const onListKey = (e: KeyboardEvent<HTMLElement>) => {
    const all = links();
    const i = all.indexOf(document.activeElement as HTMLAnchorElement);
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      all[Math.min(i + 1, all.length - 1)]?.focus();
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      if (i <= 0) inputRef.current?.focus();
      else all[i - 1]?.focus();
    } else if (e.key === 'Escape') {
      e.preventDefault();
      // Сначала фокус (он открывает панель через onFocus), потом закрываем — React применит последнее
      inputRef.current?.focus();
      setOpen(false);
    }
  };

  const showPanel = open && query.trim().length >= SUGGEST_MIN && state.status !== 'idle';
  let panel: ReactNode = null;
  if (showPanel) {
    if (state.status === 'loading') {
      panel = <p className="px-5 py-4 text-small text-text-secondary">{t('loading')}</p>;
    } else if (state.status === 'error') {
      panel = <p className="px-5 py-4 text-small text-text-secondary">{t('error')}</p>;
    } else if (state.status === 'done') {
      const { items, total, corrected, substances = [], categories = [], brands = [] } = state.result;
      const hasGroups = substances.length + categories.length + brands.length > 0;
      const hl = corrected ?? query;
      const groupLink = 'block px-5 py-2 text-body text-text outline-offset-[-2px] transition-colors hover:bg-surface-strong focus-visible:bg-surface-strong';
      const group = (title: string, children: ReactNode) => (
        <li className="pt-2">
          <p className="px-5 pb-1 text-small text-text-secondary">{title}</p>
          <ul>{children}</ul>
        </li>
      );
      panel = (
        <>
          {corrected ? (
            <p className="px-5 pt-3 text-small text-text-secondary">{t('corrected', { q: corrected })}</p>
          ) : null}
          {total === 0 ? (
            <div className="px-5 pt-4">
              <p className="text-body text-text">{t('empty', { q: query.trim() })}</p>
              {requestHref.startsWith('#') ? (
                <a href={requestHref} onClick={() => setOpen(false)} className="mt-2 inline-block text-body font-medium text-accent hover:text-accent-hover">
                  {t('emptyAction')}
                </a>
              ) : (
                <Link href={requestHref} onClick={() => setOpen(false)} className="mt-2 inline-block text-body font-medium text-accent hover:text-accent-hover">
                  {t('emptyAction')}
                </Link>
              )}
            </div>
          ) : null}
          <ul ref={listRef} className={cn('py-2', total === 0 && !hasGroups && 'hidden')}>
            {items.map((it) => (
              <li key={it.id}>
                <Link
                  data-suggest
                  href={`/product/${it.slug}/`}
                  onClick={() => setOpen(false)}
                  className="block px-5 py-2.5 outline-offset-[-2px] transition-colors hover:bg-surface-strong focus-visible:bg-surface-strong"
                >
                  <span className="chem-wrap line-clamp-1 text-body text-text">
                    <Highlight text={it.name} query={it.match === 'name' ? hl : ''} />
                  </span>
                  <span className="mt-0.5 flex flex-wrap gap-x-4 text-small text-text-secondary">
                    <span>{it.brand}</span>
                    <span className="tabular-nums">
                      {t('catalogNumber')} <Highlight text={it.catalogNumber} query={it.match === 'catalogNumber' ? hl : ''} />
                    </span>
                    {it.cas ? (
                      <span className="tabular-nums">
                        CAS <Highlight text={it.cas} query={it.match === 'cas' ? hl : ''} />
                      </span>
                    ) : null}
                    {it.formula ? (
                      <span className="text-accent">
                        <Formula value={it.formula} />
                      </span>
                    ) : null}
                  </span>
                </Link>
              </li>
            ))}
            {substances.length
              ? group(
                  t('groups.substances'),
                  substances.map((g) => (
                    <li key={g.slug}>
                      <Link data-suggest href={`/substances/${g.slug}/`} onClick={() => setOpen(false)} className={groupLink}>
                        {locale === 'en' ? g.nameEn : g.name}
                        <span className="text-text-secondary"> · {t('groups.substanceHint')}</span>
                      </Link>
                    </li>
                  )),
                )
              : null}
            {categories.length
              ? group(
                  t('groups.categories'),
                  categories.map((g) => (
                    <li key={g.href}>
                      <Link data-suggest href={g.href} onClick={() => setOpen(false)} className={groupLink}>
                        {g.name}
                      </Link>
                    </li>
                  )),
                )
              : null}
            {brands.length
              ? group(
                  t('groups.brands'),
                  brands.map((g) => (
                    <li key={g.slug}>
                      <Link data-suggest href={`/brands/${g.slug}/`} onClick={() => setOpen(false)} className={groupLink}>
                        {g.name}
                      </Link>
                    </li>
                  )),
                )
              : null}
          </ul>
          {total > items.length ? (
            <button
              type="submit"
              className="block w-full bg-surface-strong px-5 py-3 text-left text-small font-medium text-accent transition-colors hover:text-accent-hover"
            >
              {t('allResults', { n: total })}
            </button>
          ) : total === 0 ? (
            <div className="h-3" />
          ) : null}
        </>
      );
    }
  }

  const status =
    state.status === 'done' ? (state.result.total ? t('found', { n: state.result.total }) : t('empty', { q: query.trim() })) : '';

  return (
    <form
      ref={rootRef}
      role="search"
      action={action}
      method="get"
      className={cn('relative w-full', className)}
      onSubmit={(e) => {
        if (!query.trim()) {
          e.preventDefault();
          inputRef.current?.focus();
          return;
        }
        track('site_search', { query: query.trim(), place, mode: 'submit' });
      }}
      onBlur={(e) => {
        if (!e.currentTarget.contains(e.relatedTarget as Node | null)) setOpen(false);
      }}
    >
      <label htmlFor={fieldId} className="sr-only">
        {t('label')}
      </label>
      <Search
        aria-hidden
        size={lg ? 22 : 18}
        strokeWidth={1.5}
        className={cn('pointer-events-none absolute top-1/2 -translate-y-1/2 text-text-secondary', lg ? 'left-5' : 'left-4')}
      />
      <input
        ref={inputRef}
        id={fieldId}
        type="search"
        name="q"
        value={query}
        onChange={(e) => {
          setQuery(e.target.value);
          setOpen(true);
        }}
        onFocus={() => setOpen(true)}
        onKeyDown={onInputKey}
        aria-controls={listId}
        autoComplete="off"
        autoFocus={autoFocus}
        enterKeyHint="search"
        spellCheck={false}
        placeholder={t('placeholder')}
        className={cn(
          'ym-disable-keys w-full rounded-pill border bg-base text-text outline-offset-0 transition-colors placeholder:text-text-placeholder hover:border-text-secondary focus-visible:border-accent',
          lg ? 'h-16 border-border pl-14 pr-[7.5rem] text-lead' : 'h-11 border-border bg-base/50 pl-11 pr-[5.5rem] text-body',
          inputClassName,
        )}
      />
      <button
        type="submit"
        className={cn(
          'absolute rounded-pill bg-accent font-medium text-text-on-accent transition-colors hover:bg-accent-hover',
          lg ? 'right-2 top-2 h-12 px-6 text-body' : 'right-1 top-1 h-9 px-4 text-small',
        )}
      >
        {t('submit')}
      </button>

      <p className="sr-only" aria-live="polite">
        {status}
      </p>

      <div
        id={listId}
        onKeyDown={onListKey}
        hidden={!showPanel}
        className="absolute inset-x-0 top-full z-50 mt-2 overflow-hidden rounded-field bg-surface-raised shadow-[0_8px_24px_rgb(0_0_0/0.35)]" // taste-skill-ignore: выпадающие подсказки поверх страницы
      >
        {panel}
      </div>
    </form>
  );
}
