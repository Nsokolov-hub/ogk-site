'use client';

import { useEffect, useState } from 'react';
import type { HomeContent } from '@/types/content';
import { Container } from '@/components/ui/Container';
import { Link } from '@/i18n/navigation';
import { CapabilitiesLogo } from './CapabilitiesLogo';
import { cn } from '@/lib/cn';
import { usePrefersReducedMotion } from '@/lib/hooks';

const INTERVAL_MS = 3000;

/**
 * «У нас вы сможете»: строки сменяются каждые 3 с и замирают, пока на них мышь или фокус; при «меньше движения»
 * в настройках системы показаны списком. Справа — чёткий логотип без эффектов.
 * Все 12 строк — ссылки и все есть в HTML: это внутренняя перелинковка на разделы и услуги.
 */
export function CapabilitiesSection({ capabilities }: { capabilities: HomeContent['capabilities'] }) {
  const reducedMotion = usePrefersReducedMotion();
  const { items } = capabilities;
  const [index, setIndex] = useState(0);
  const [hovered, setHovered] = useState(false);
  const running = !hovered && !reducedMotion;

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
                      'col-start-1 row-start-1 text-h3 font-medium text-text ease-out',
                      active
                        ? 'visible translate-y-0 opacity-100 [transition:transform_0.5s,opacity_0.5s,visibility_0s]'
                        : cn(
                            'invisible opacity-0 [transition:transform_0.5s,opacity_0.5s,visibility_0s_linear_0.5s]',
                            before ? '-translate-y-6' : 'translate-y-6',
                          ),
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
        </div>

        <CapabilitiesLogo />
      </Container>
    </section>
  );
}
