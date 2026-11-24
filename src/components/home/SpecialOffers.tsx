'use client';

import { useCallback, useEffect, useRef, useState } from 'react';
import Image from 'next/image';
import { useTranslations } from 'next-intl';
import { Container } from '@/components/ui/Container';
import { SectionHeading } from '@/components/ui/SectionHeading';
import { Link } from '@/i18n/navigation';
import { PlaybackButton } from './PlaybackButton';
import { useCarouselPlayback } from './useCarouselPlayback';

const offers = [
  { id: 'keys', href: '/catalog/pharmacopeias/', image: '/images/home/offers/pharmacopoeias.webp' },
  { id: 'glucose', href: '/product/aozeal-d0147-28-alpha-d-glucose-monohydrate-working-standard/', image: '/images/home/offers/aozeal-d0147-28.webp' },
  { id: 'lgc', href: '/brands/lgc/', image: '/images/brands/lgc.svg' },
  { id: 'customs', href: '/services/customs-clearance/', image: '/images/home/offers/customs.webp' },
  { id: 'stock', href: '/catalog/', image: '/images/brand/logo-eng.svg' },
] as const;

export function SpecialOffers() {
  const t = useTranslations('home.offers');
  const rail = useRef<HTMLDivElement>(null);
  const gesture = useRef<{ x: number; left: number; dragged: boolean } | null>(null);
  const cancelClick = useRef(false);
  const [visibleCards, setVisibleCards] = useState(3);
  const [page, setPage] = useState(0);
  const pageCount = Math.ceil(offers.length / visibleCards);

  const moveTo = useCallback((index: number) => {
    const el = rail.current;
    if (!el) return;
    const card = el.children[Math.min(index * visibleCards, offers.length - visibleCards)] as HTMLElement;
    el.scrollTo({ left: card.offsetLeft, behavior: matchMedia('(prefers-reduced-motion: reduce)').matches ? 'instant' : 'smooth' });
  }, [visibleCards]);
  const advance = useCallback(() => moveTo((page + 1) % pageCount), [moveTo, page, pageCount]);
  const playback = useCarouselPlayback(advance, pageCount > 1, 8000);

  useEffect(() => {
    const el = rail.current;
    if (!el) return;
    const resize = new ResizeObserver(() => {
      const card = el.firstElementChild as HTMLElement;
      setVisibleCards(Math.max(1, Math.round(el.clientWidth / card.offsetWidth)));
    });
    resize.observe(el);
    return () => resize.disconnect();
  }, []);

  function endDrag(el: HTMLDivElement) {
    if (gesture.current?.dragged) {
      const { left } = gesture.current;
      const cards = Array.from(el.children) as HTMLElement[];
      const distance = el.scrollLeft - left;
      const near = (position: number) => cards.reduce((best, card) =>
        Math.abs(card.offsetLeft - position) < Math.abs(best.offsetLeft - position) ? card : best);
      const origin = cards.indexOf(near(left));
      const nearest = near(el.scrollLeft);
      const target = Math.abs(distance) > 36 && cards.indexOf(nearest) === origin
        ? cards[Math.max(0, Math.min(cards.length - 1, origin + Math.sign(distance)))] : nearest;
      delete el.dataset.dragging;
      el.scrollTo({ left: target.offsetLeft, behavior: matchMedia('(prefers-reduced-motion: reduce)').matches ? 'instant' : 'smooth' });
      cancelClick.current = true;
    }
    gesture.current = null;
  }

  return (
    <section aria-labelledby="offers-title" className="mt-16">
      <Container>
        <SectionHeading id="offers-title" title={t('title')} accent={t('accent')} subtitle={t('subtitle')} />
        <div ref={playback.ref} role="region" aria-roledescription="carousel" aria-labelledby="offers-title">
          <div ref={rail} className="offer-rail" onScroll={(event) => {
            const el = event.currentTarget;
            const max = el.scrollWidth - el.clientWidth;
            setPage(max > 0 ? Math.round(el.scrollLeft / max * (pageCount - 1)) : 0);
          }} onDragStart={(e) => e.preventDefault()}
          onPointerDown={(e) => {
            cancelClick.current = false;
            if (e.pointerType === 'mouse' && e.button === 0) gesture.current = { x: e.clientX, left: e.currentTarget.scrollLeft, dragged: false };
          }}
          onPointerMove={(e) => {
            const drag = gesture.current;
            if (!drag || e.buttons !== 1) return;
            const dx = e.clientX - drag.x;
            if (!drag.dragged && Math.abs(dx) < 6) return;
            if (!drag.dragged) {
              drag.dragged = true;
              e.currentTarget.dataset.dragging = 'true';
              e.currentTarget.setPointerCapture(e.pointerId);
            }
            e.currentTarget.scrollLeft = drag.left - dx;
          }}
          onPointerUp={(e) => endDrag(e.currentTarget)} onPointerCancel={(e) => endDrag(e.currentTarget)}
          onClickCapture={(e) => {
            if (cancelClick.current && e.detail > 0) { e.preventDefault(); e.stopPropagation(); cancelClick.current = false; }
          }}>
            {offers.map(({ id, href, image }) => (
              <Link key={id} href={href} draggable={false} className="offer-card group" aria-labelledby={`offer-${id}`}>
                <div className={`offer-art offer-art-${id}`}>
                  <Image src={image} alt="" fill draggable={false} sizes="(min-width: 1024px) 30vw, (min-width: 768px) 45vw, 85vw" />
                </div>
                <h3 id={`offer-${id}`} className="mt-6 text-[clamp(1.35rem,2.36vw,2.125rem)] leading-[1.14] font-medium">{t(`${id}.title`)}</h3>
                <p className="mb-6 mt-4 text-[clamp(1rem,1.67vw,1.5rem)] leading-[1.2] text-text-secondary">{t(`${id}.text`)}</p>
                <span className="mt-auto flex min-h-12 items-center justify-center rounded-pill border border-accent/55 text-accent transition-colors group-hover:bg-accent group-hover:text-base">{t('more')}</span>
              </Link>
            ))}
          </div>
          <div className="relative mt-5 flex min-h-10 items-center justify-center gap-2">
            {Array.from({ length: pageCount }, (_, index) => (
              <button key={index} type="button" onClick={() => moveTo(index)} aria-label={t('page', { page: index + 1 })} aria-current={page === index ? 'true' : undefined}
                className="group grid h-10 w-12 place-items-center md:w-16">
                <span className="h-1 w-full rounded-full bg-text-secondary/40 group-aria-[current=true]:bg-accent" />
              </button>
            ))}
            <div className="absolute right-0"><PlaybackButton {...playback} /></div>
          </div>
        </div>
      </Container>
    </section>
  );
}
