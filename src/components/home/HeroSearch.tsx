'use client';

import { useEffect, useRef, useState } from 'react';
import { useTranslations } from 'next-intl';
import type { HomeContent } from '@/types/content';
import { SearchBox } from '@/components/search/SearchBox';
import { Container } from '@/components/ui/Container';

/**
 * Поиск на первом экране. Покупатель ОГК-ХИМ приходит с каталожным номером, CAS или списком позиций (ТЗ 3),
 * поэтому главное действие главной — найти позицию или прислать список, а не листать витрину.
 * Пока блок на экране, поиск в шапке скрыт, чтобы не было двух одинаковых полей рядом.
 */
export function HeroSearch({ search, facts }: Pick<HomeContent['hero'], 'search' | 'facts'>) {
  const t = useTranslations('home.heroSearch');
  const [query, setQuery] = useState('');
  const ref = useRef<HTMLElement>(null);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const root = document.documentElement;
    const io = new IntersectionObserver(([entry]) => {
      root.dataset.heroSearch = entry.isIntersecting ? 'in' : 'out';
    });
    io.observe(el);
    return () => {
      io.disconnect();
      delete root.dataset.heroSearch;
    };
  }, []);

  return (
    <section ref={ref} aria-labelledby="hero-search-title" className="relative z-30">
      <Container>
        <div className="enter grid gap-8 rounded-block bg-surface-raised p-5 [--enter-i:3] sm:p-8 lg:grid-cols-[minmax(0,1fr)_minmax(0,300px)] lg:gap-14 lg:p-10 xl:grid-cols-[minmax(0,1fr)_minmax(0,360px)]">
          <div className="min-w-0">
            <h2 id="hero-search-title" className="max-w-[640px] text-h3 font-medium text-text">
              {search.title}
            </h2>
            <SearchBox size="lg" value={query} onValueChange={setQuery} requestHref="#request" place="hero" className="mt-5 lg:mt-6" />
            <div className="mt-4 flex flex-wrap items-center gap-x-1 gap-y-2 text-small">
              <span className="mr-2 text-text-secondary">{t('examples')}</span>
              {search.examples.map((q) => (
                <button
                  key={q}
                  type="button"
                  aria-label={t('exampleLabel', { q })}
                  onClick={() => {
                    setQuery(q);
                    // Фокус в поле — сразу видны подсказки
                    ref.current?.querySelector<HTMLInputElement>('input[type="search"]')?.focus();
                  }}
                  className="h-9 rounded-pill bg-surface-strong px-3.5 text-text transition-colors hover:text-accent"
                >
                  {q}
                </button>
              ))}
            </div>
            <p className="mt-6 text-body text-text">
              {t('list')}{' '}
              <a href="#request" className="whitespace-nowrap font-medium text-accent underline-offset-4 hover:text-accent-hover hover:underline">
                {t('listAction')}
              </a>
            </p>
          </div>

          {/* На телефоне — строками «цифра + подпись», на планшете — в ряд, на десктопе — колонкой справа */}
          <dl className="grid gap-3 sm:grid-cols-3 sm:gap-6 lg:grid-cols-1 lg:content-center">
            {facts.map((f) => (
              <div key={f.label} className="flex flex-row-reverse items-baseline justify-end gap-3 sm:flex-col-reverse sm:items-start sm:gap-1">
                <dt className="text-body text-text-secondary">{f.label}</dt>
                <dd className="text-h3 font-medium text-accent">{f.value}</dd>
              </div>
            ))}
          </dl>
        </div>
      </Container>
    </section>
  );
}
