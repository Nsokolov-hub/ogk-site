'use client';

import { useEffect, useState } from 'react';
import Image from 'next/image';
import { Pause, Play } from 'lucide-react';
import { useTranslations } from 'next-intl';
import type { HomeContent } from '@/types/content';
import { Container } from '@/components/ui/Container';
import { Link } from '@/i18n/navigation';
import { cn } from '@/lib/cn';
import { usePrefersReducedMotion } from '@/lib/hooks';

const INTERVAL_MS = 3000;

/**
 * «У нас вы сможете»: строки сменяются каждые 3 с, есть пауза (WCAG 2.2.2).
 * Все 12 строк — ссылки и все есть в HTML: это внутренняя перелинковка на разделы и услуги.
 */
export function CapabilitiesSection({ capabilities }: { capabilities: HomeContent['capabilities'] }) {
  const t = useTranslations('home.capabilities');
  const reducedMotion = usePrefersReducedMotion();
  const { items } = capabilities;
  const [index, setIndex] = useState(0);
  const [paused, setPaused] = useState(false);
  const [hovered, setHovered] = useState(false);
  const running = !paused && !hovered && !reducedMotion;

  useEffect(() => {
    if (!running) return;
    const id = window.setInterval(() => setIndex((i) => (i + 1) % items.length), INTERVAL_MS);
    return () => window.clearInterval(id);
  }, [running, items.length]);

  return (
    <section aria-labelledby="cap-title" className="relative mt-20 overflow-hidden md:mt-30 lg:mt-40">
      <Container className="grid items-center gap-10 lg:grid-cols-[minmax(0,1fr)_minmax(0,1fr)]">
        <div
          onMouseEnter={() => setHovered(true)}
          onMouseLeave={() => setHovered(false)}
          onFocusCapture={() => setHovered(true)}
          onBlurCapture={() => setHovered(false)}
        >
          <h2 id="cap-title" className="text-h2 font-medium text-text">
            {capabilities.title}
          </h2>

          {reducedMotion ? (
            <ul className="mt-6 flex flex-col gap-3">
              {items.map((c) => (
                <li key={c.id} className="text-lead font-medium">
                  <Link href={c.href} className="transition-colors hover:text-accent-hover">
                    {c.prefix} <span className="text-accent">{c.accent}</span> {c.suffix}
                  </Link>
                </li>
              ))}
            </ul>
          ) : (
            <ul className="mt-6 grid md:mt-8">
              {items.map((c, i) => {
                const active = i === index;
                const before = i === (index - 1 + items.length) % items.length;
                return (
                  <li
                    key={c.id}
                    inert={!active}
                    className={cn(
                      'col-start-1 row-start-1 text-h3 font-medium text-text transition-[transform,opacity] duration-500 ease-out',
                      active ? 'translate-y-0 opacity-100' : before ? '-translate-y-6 opacity-0' : 'translate-y-6 opacity-0',
                    )}
                  >
                    <Link href={c.href} className="transition-colors hover:text-accent-hover">
                      {c.prefix} <span className="text-accent">{c.accent}</span> {c.suffix}
                    </Link>
                  </li>
                );
              })}
            </ul>
          )}

          {!reducedMotion ? (
            <button
              type="button"
              onClick={() => setPaused((p) => !p)}
              aria-label={paused ? t('play') : t('pause')}
              className="mt-8 inline-grid size-11 place-items-center rounded-full border border-border text-text-secondary transition-colors hover:border-accent hover:text-accent"
            >
              {paused ? <Play aria-hidden size={18} strokeWidth={1.5} /> : <Pause aria-hidden size={18} strokeWidth={1.5} />}
            </button>
          ) : null}
        </div>

        <div aria-hidden className="relative">
          <Image src="/images/home/logo-blur.png" alt="" width={1284} height={548} sizes="(min-width: 1024px) 45vw, 90vw" className="h-auto w-full" />
        </div>
      </Container>
    </section>
  );
}
