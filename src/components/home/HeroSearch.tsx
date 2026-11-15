'use client';

import { useEffect, useRef, useState } from 'react';
import { useTranslations } from 'next-intl';
import type { HomeContent } from '@/types/content';
import { Button } from '@/components/ui/Button';
import { SearchBox } from '@/components/search/SearchBox';
import { Container } from '@/components/ui/Container';

/**
 * Поиск на первом экране. Покупатель ОГК-ХИМ приходит с каталожным номером, CAS или списком позиций (ТЗ 3),
 * поэтому главное действие главной — найти позицию или прислать список, а не листать витрину.
 * Пока блок на экране, поиск в шапке скрыт, чтобы не было двух одинаковых полей рядом.
 */
export function HeroSearch({ search, facts, intro }: Pick<HomeContent['hero'], 'search' | 'facts'> & { intro: HomeContent['hero']['slides'][number] }) {
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
    <section ref={ref} aria-labelledby="hero-title" className="relative z-30 pt-[104px] lg:pt-[164px]">
      <Container>
        <div className="mb-6 max-w-[960px] lg:mb-8">
          <h1 id="hero-title" className="text-h2 font-medium text-text lg:text-h1">{intro.title}</h1>
          {intro.subtitle ? <p className="mt-3 text-body text-text-secondary md:text-lead">{intro.subtitle}</p> : null}
        </div>
        <div className="enter grid gap-6 rounded-block bg-surface-raised p-5 [--enter-i:1] sm:p-8 lg:grid-cols-[minmax(0,1fr)_minmax(0,340px)] lg:gap-10 lg:p-8">
          <div className="min-w-0">
            <h2 id="hero-search-title" className="max-w-[640px] text-body font-medium text-text md:text-h4">
              {search.title}
            </h2>
            <SearchBox size="lg" value={query} onValueChange={setQuery} requestHref="/rfq/#file" place="hero" className="mt-4" />
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
          </div>
          <div className="flex flex-col items-start justify-center gap-3 rounded-field bg-surface-strong p-4 sm:p-5">
            <h2 className="text-h4 font-medium text-text">{t('fileTitle')}</h2>
            <p className="text-small text-text-secondary">{t('fileText')}</p>
            <Button href="/rfq/#file" size="m" className="w-full">{t('listAction')}</Button>
            <Button href="/rfq/#bulk" size="s" variant="ghost" className="h-auto min-h-9 whitespace-normal text-left">{t('parseList')}</Button>
          </div>
        </div>
          <dl className="mt-5 grid gap-3 sm:grid-cols-3 sm:gap-6">
            {facts.map((f) => (
              <div key={f.label} className="flex flex-row-reverse items-baseline justify-end gap-3 sm:justify-center">
                <dt className="text-body text-text-secondary">{f.label}</dt>
                <dd className="text-h4 font-medium text-accent">{f.value}</dd>
              </div>
            ))}
          </dl>
      </Container>
    </section>
  );
}
