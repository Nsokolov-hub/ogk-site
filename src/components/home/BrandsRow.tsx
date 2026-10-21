'use client';

import { useCallback, useEffect, useRef, useState } from 'react';
import Image from 'next/image';
import { useTranslations } from 'next-intl';
import type { BrandRef } from '@/types/catalog';
import { RoundArrowButton } from '@/components/ui/RoundArrowButton';
import { Link } from '@/i18n/navigation';

/** Лента логотипов брендов со стрелками; без автопрокрутки */
export function BrandsRow({ items }: { items: BrandRef[] }) {
  const t = useTranslations('home.brands');
  const listRef = useRef<HTMLUListElement>(null);
  const [edges, setEdges] = useState({ start: true, end: false });

  const update = useCallback(() => {
    const el = listRef.current;
    if (!el) return;
    setEdges({ start: el.scrollLeft <= 4, end: el.scrollLeft + el.clientWidth >= el.scrollWidth - 4 });
  }, []);

  useEffect(() => {
    update();
    const el = listRef.current;
    if (!el) return;
    el.addEventListener('scroll', update, { passive: true });
    window.addEventListener('resize', update);
    return () => {
      el.removeEventListener('scroll', update);
      window.removeEventListener('resize', update);
    };
  }, [update]);

  const scroll = (dir: 1 | -1) => {
    const el = listRef.current;
    if (el) el.scrollBy({ left: dir * el.clientWidth * 0.8, behavior: 'smooth' });
  };

  return (
    <div>
      <ul ref={listRef} className="scroll-row -mx-4 gap-3 px-4 md:-mx-6 md:gap-4 md:px-6 lg:mx-0 lg:px-0">
        {items.map((b) => (
          <li key={b.slug}>
            <Link
              href={`/brands/${b.slug}/`}
              aria-label={t('brandLink', { brand: b.name })}
              className="glow grid h-[100px] w-[124px] place-items-center overflow-hidden rounded-card bg-surface md:h-[140px] md:w-[172px] md:rounded-block lg:h-[172px] lg:w-[212px]"
            >
              {b.logo ? (
                <Image src={b.logo} alt="" width={212} height={172} unoptimized className="h-full w-full object-contain" />
              ) : (
                <span className="text-h4 font-medium text-text">{b.name}</span>
              )}
            </Link>
          </li>
        ))}
      </ul>
      <div className="mt-4 hidden justify-end gap-2 md:flex">
        <RoundArrowButton label={t('prev')} direction="left" disabled={edges.start} onClick={() => scroll(-1)} />
        <RoundArrowButton label={t('next')} direction="right" disabled={edges.end} onClick={() => scroll(1)} />
      </div>
    </div>
  );
}
