'use client';

import { useCallback, useRef, useState } from 'react';
import Image from 'next/image';
import { ArrowRight, Globe, Plus, ShieldCheck } from 'lucide-react';
import { useTranslations } from 'next-intl';
import type { Cta, HomeContent, HeroSlide } from '@/types/content';
import { Button } from '@/components/ui/Button';
import { Container } from '@/components/ui/Container';
import { RoundArrowButton } from '@/components/ui/RoundArrowButton';
import { cn } from '@/lib/cn';

function CtaIcon({ icon }: { icon?: Cta['icon'] }) {
  if (icon === 'plus') return <Plus aria-hidden size={20} strokeWidth={2} />;
  if (icon === 'arrow') return <ArrowRight aria-hidden size={20} strokeWidth={2} />;
  if (icon === 'dot') return <span aria-hidden className="size-1.5 rounded-full bg-current" />;
  return null;
}

function SlideVisual({ slide, priority }: { slide: HeroSlide; priority: boolean }) {
  if (slide.imageMode === 'cover') {
    return (
      <div aria-hidden className="absolute inset-0 -z-10 overflow-hidden">
        <Image
          src={slide.image.src}
          alt=""
          fill
          priority={priority}
          sizes="100vw"
          className="animate-hero-zoom object-cover object-[60%_25%] md:object-[55%_20%]"
        />
        <div className="absolute inset-0 bg-gradient-to-t from-base via-base/40 to-base/10" />
        <div className="absolute inset-0 bg-gradient-to-r from-base/70 via-transparent to-transparent" />
      </div>
    );
  }
  return (
    <div aria-hidden className="absolute inset-0 -z-10 overflow-hidden">
      <div className="absolute right-[-10%] top-[8%] size-[min(110vw,900px)] rounded-full bg-[radial-gradient(circle,rgb(130_238_141/0.16)_0%,transparent_62%)]" />
      <div className="absolute right-4 top-[22%] h-[30%] w-[60%] md:right-[5%] md:top-[30%] md:h-[48%] md:w-[38%]">
        <Image src={slide.image.src} alt="" fill sizes="(min-width: 768px) 38vw, 60vw" className="object-contain object-right" />
      </div>
      <div className="absolute inset-0 bg-gradient-to-t from-base via-base/30 to-transparent" />
    </div>
  );
}

/**
 * Первый экран (ТЗ 11.2): несколько слайдов, переключение по клику, без автопрокрутки.
 * Заголовок первого слайда — единственный h1 страницы.
 */
export function HeroSlider({ badges, slides }: HomeContent['hero']) {
  const t = useTranslations('home.hero');
  const [index, setIndex] = useState(0);
  const total = slides.length;
  const go = useCallback((i: number) => setIndex(((i % total) + total) % total), [total]);
  const swipeStart = useRef<number | null>(null);

  return (
    <section aria-labelledby="hero-title" className="relative isolate overflow-hidden">
      <div
        role="region"
        aria-roledescription="carousel"
        aria-label={t('region')}
        className="relative grid min-h-[clamp(640px,100svh,940px)] touch-pan-y"
        onKeyDown={(e) => {
          if (e.key === 'ArrowRight') go(index + 1);
          if (e.key === 'ArrowLeft') go(index - 1);
        }}
        onPointerDown={(e) => {
          if (e.pointerType !== 'mouse') swipeStart.current = e.clientX;
        }}
        onPointerUp={(e) => {
          if (swipeStart.current === null) return;
          const dx = e.clientX - swipeStart.current;
          swipeStart.current = null;
          if (Math.abs(dx) > 50) go(index + (dx < 0 ? 1 : -1));
        }}
      >
        {slides.map((s, i) => {
          const active = i === index;
          const Heading = i === 0 ? 'h1' : 'h2';
          return (
            <div
              key={s.id}
              role="group"
              aria-roledescription="slide"
              aria-label={t('slide', { current: i + 1, total })}
              inert={!active}
              className={cn(
                'relative isolate col-start-1 row-start-1 flex transition-opacity duration-700 ease-out',
                active ? 'z-10 opacity-100' : 'z-0 opacity-0',
              )}
            >
              <SlideVisual slide={s} priority={i === 0} />
              <Container className="flex flex-col justify-end pb-32 pt-44 md:pb-36 lg:pb-40 lg:pt-56">
                <div className={cn('max-w-[1080px]', s.imageMode === 'object' && 'md:max-w-[56%]')}>
                  <Heading id={i === 0 ? 'hero-title' : undefined} className="text-h1 font-medium uppercase text-text">
                    {s.title}
                  </Heading>
                  <p className="mt-4 max-w-[620px] text-lead text-text-secondary md:mt-6">{s.subtitle}</p>
                  <div className="mt-8 flex flex-wrap gap-3 md:mt-10">
                    {s.ctas.map((c) => (
                      <Button key={c.label} href={c.href} variant={c.variant} size="m" icon={<CtaIcon icon={c.icon} />}>
                        {c.label}
                      </Button>
                    ))}
                  </div>
                </div>
              </Container>
            </div>
          );
        })}

        {/* Бейджи сверху */}
        <Container className="pointer-events-none absolute inset-x-0 top-0 z-20 flex justify-between gap-6 pt-[104px] lg:pt-[164px]">
          <p className="flex items-center gap-3 text-small text-text md:text-body">
            <span className="grid size-10 shrink-0 place-items-center rounded-full border border-accent/50 md:size-12">
              <ShieldCheck aria-hidden size={22} strokeWidth={1.5} className="text-accent" />
            </span>
            <span>
              {badges.trust}
              <br />
              <span className="text-accent">{badges.trustAccent}</span>
            </span>
          </p>
          <p className="hidden items-center gap-3 text-right text-body text-text sm:flex">
            <span>
              <span className="text-accent">{badges.makersAccent}</span> {badges.makers.split(' ')[0]}
              <br />
              {badges.makers.split(' ').slice(1).join(' ')}
            </span>
            <span className="grid size-12 shrink-0 place-items-center rounded-full border border-accent/50">
              <Globe aria-hidden size={22} strokeWidth={1.5} className="text-accent" />
            </span>
          </p>
        </Container>

        {/* Управление слайдами */}
        <Container className="absolute inset-x-0 bottom-0 z-20 flex items-center justify-between gap-4 pb-8 md:pb-10">
          <div className="flex items-center gap-1">
            {slides.map((s, i) => (
              <button
                key={s.id}
                type="button"
                aria-label={t('goTo', { n: i + 1 })}
                aria-current={i === index ? 'true' : undefined}
                onClick={() => go(i)}
                className="group grid h-11 place-items-center px-1"
              >
                <span
                  className={cn(
                    'block h-1.5 rounded-pill transition-all duration-300',
                    i === index ? 'w-10 bg-accent' : 'w-4 bg-text-secondary/50 group-hover:bg-text-secondary',
                  )}
                />
              </button>
            ))}
          </div>
          <div className="flex gap-2">
            <RoundArrowButton label={t('prev')} direction="left" onClick={() => go(index - 1)} />
            <RoundArrowButton label={t('next')} direction="right" onClick={() => go(index + 1)} />
          </div>
        </Container>
      </div>
    </section>
  );
}
