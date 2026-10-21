'use client';

import { useCallback, useRef, useState, type CSSProperties } from 'react';
import Image from 'next/image';
import { useTranslations } from 'next-intl';
import type { HomeContent, HeroSlide } from '@/types/content';
import { Button } from '@/components/ui/Button';
import { Container } from '@/components/ui/Container';
import { RoundArrowButton } from '@/components/ui/RoundArrowButton';
import { cn } from '@/lib/cn';

const enter = (i: number) => ({ '--enter-i': i }) as CSSProperties;

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
        {/* Нейтральная подложка под текстом поверх фото — для читаемости */}
        <div className="absolute inset-0 bg-gradient-to-t from-base via-base/45 to-base/10" /* taste-skill-ignore */ />
        <div className="absolute inset-0 bg-gradient-to-r from-base/75 via-base/20 to-transparent" /* taste-skill-ignore */ />
      </div>
    );
  }
  return (
    <div aria-hidden className="absolute inset-0 -z-10 overflow-hidden">
      <div className="absolute right-4 top-[20%] h-[30%] w-[58%] md:right-[4%] md:top-[24%] md:h-[58%] md:w-[38%]">
        <Image src={slide.image.src} alt="" fill sizes="(min-width: 768px) 38vw, 60vw" className="object-contain object-right" />
      </div>
    </div>
  );
}

/**
 * Первый экран (ТЗ 11.2): несколько слайдов, переключение по клику, без автопрокрутки.
 * Заголовок первого слайда — единственный h1 страницы (текст из ТЗ 10.3).
 * Поиск по кат. № и CAS — отдельным блоком сразу под слайдами (HeroSearch).
 */
export function HeroSlider({ slides }: Pick<HomeContent['hero'], 'slides'>) {
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
        className="relative grid min-h-[clamp(560px,70svh,780px)] touch-pan-y"
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
                'relative isolate col-start-1 row-start-1 flex',
                // Неактивный слайд сначала гаснет, потом становится невидимым — и не перекрывает текст активного
                // При «уменьшении движения» смены нет — неактивные слайды просто не показываются
                active
                  ? 'visible z-10 opacity-100 [transition:opacity_0.6s_ease-out,visibility_0s]'
                  : 'invisible z-0 opacity-0 [transition:opacity_0.6s_ease-out,visibility_0s_linear_0.6s] motion-reduce:hidden',
              )}
            >
              <SlideVisual slide={s} priority={i === 0} />
              <Container className="flex flex-col justify-end pb-24 pt-40 md:pb-28 lg:pt-48">
                <div className={cn(s.imageMode === 'cover' ? 'max-w-[1120px]' : 'max-w-[1120px] md:max-w-[60%]')}>
                  <Heading
                    id={i === 0 ? 'hero-title' : undefined}
                    style={enter(0)}
                    className="enter text-h1 font-medium text-text"
                  >
                    {s.title}
                  </Heading>
                  <p style={enter(1)} className="enter mt-4 max-w-[620px] text-lead text-text md:mt-5">
                    {s.subtitle}
                  </p>
                  <div style={enter(2)} className="enter mt-7 flex flex-wrap gap-3 md:mt-8">
                    {s.ctas.map((c) => (
                      <Button key={c.label} href={c.href} variant={c.variant} size="m">
                        {c.label}
                      </Button>
                    ))}
                  </div>
                </div>
              </Container>
            </div>
          );
        })}

        {/* Переключение слайдов: точки и стрелки */}
        <Container className="absolute inset-x-0 bottom-0 z-20 flex items-center justify-between gap-4 pb-6 md:pb-8">
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
                    'block h-1.5 rounded-pill transition-[width,background-color] duration-300',
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
