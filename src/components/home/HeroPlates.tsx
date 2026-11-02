'use client';

import { useCallback, useEffect, useRef, useState, type CSSProperties, type ReactNode } from 'react';
import Image from 'next/image';
import { useTranslations } from 'next-intl';
import type { HeroSlide } from '@/types/content';
import { Button } from '@/components/ui/Button';
import { ArrowDownRightIcon } from '@/components/ui/DesignIcons';

/** Размер из макета плашки 1236 × 582 в единицах плашки (--u, globals.css → .hero-plates) */
const u = (px: number) => `calc(${px} * var(--u))`;
const box = (s: Record<string, number>): CSSProperties =>
  Object.fromEntries(Object.entries(s).map(([k, v]) => [k, u(v)])) as CSSProperties;

const DIR = '/images/home/plates';
const MOVE_MS = 700;

function ReferenceVisual({ priority }: { priority: boolean }) {
  return (
    <>
      <div className="absolute" style={box({ left: 363, top: -291, width: 1746, height: 1746 })}>
        <Image src={`${DIR}/circles.svg`} alt="" fill unoptimized />
      </div>
      <div className="absolute grid place-items-center" style={box({ right: -165, top: -51, width: 822.896, height: 822.896 })}>
        {/* В макете на этом слое размытие 2 px; на сайте в натуральную величину оно заметно, бизнес попросил чётко */}
        <div className="relative rotate-15" style={box({ width: 671.892, height: 671.892 })}>
          <Image quality={90} src={`${DIR}/merck.webp`} alt="" fill priority={priority} sizes="(min-width: 1024px) 672px, 340px" className="object-cover" />
        </div>
      </div>
      <div className="absolute grid place-items-center" style={box({ right: 171.85, top: 61.17, width: 564.15, height: 564.15 })}>
        <div
          className="relative -rotate-15 [filter:drop-shadow(15px_8px_16.7px_rgb(0_0_0/0.25))]"
          style={box({ width: 460.627, height: 460.627 })}
        >
          <Image quality={90} src={`${DIR}/usp.webp`} alt="" fill priority={priority} sizes="(min-width: 1024px) 461px, 240px" className="object-cover" />
        </div>
      </div>
    </>
  );
}

function ChromatographyVisual() {
  return (
    <>
      <div className="absolute" style={box({ left: 443, top: -127, width: 660, height: 660 })}>
        <Image src={`${DIR}/ellipse-glow.svg`} alt="" fill unoptimized />
      </div>
      <div className="absolute grid place-items-center" style={box({ right: -152.78, top: -187.1, width: 946.038, height: 1228.515 })}>
        <div className="relative -rotate-30" style={box({ width: 410.072, height: 1181.812 })}>
          <Image quality={90} src={`${DIR}/column.webp`} alt="" fill sizes="(min-width: 1024px) 410px, 210px" className="object-fill" />
        </div>
      </div>
    </>
  );
}

function LogisticsVisual() {
  return (
    <>
      <div className="absolute grid place-items-center" style={box({ left: 590.47, top: -175.22, width: 847.821, height: 847.821 })}>
        <div
          className="rotate-45 bg-gradient-to-b from-accent to-[#4a8851] opacity-[0.02]"
          style={{ ...box({ width: 488, height: 711 }), filter: `blur(${u(50)})` }}
        />
      </div>
      <div className="absolute grid place-items-center" style={box({ left: 55.19, top: 36.91, width: 1170.262, height: 1170.262 })}>
        <div className="relative -rotate-135" style={box({ width: 461, height: 1194 })}>
          <Image quality={90} src={`${DIR}/transport.webp`} alt="" fill sizes="(min-width: 1024px) 461px, 240px" className="object-fill" />
        </div>
      </div>
      <div className="absolute grid place-items-center" style={box({ left: 873.5, top: -360.07, width: 724.006, height: 720.149 })}>
        <div className="relative rotate-[-0.31deg]" style={box({ width: 720.099, height: 716.221 })}>
          <Image src={`${DIR}/logistics-shape.svg`} alt="" fill unoptimized />
        </div>
      </div>
    </>
  );
}

function Visual({ plate, priority }: { plate: HeroSlide['plate']; priority: boolean }) {
  if (plate === 'chromatography') return <ChromatographyVisual />;
  if (plate === 'logistics') return <LogisticsVisual />;
  return <ReferenceVisual priority={priority} />;
}

/** Часть текста, выделенная зелёным (как в макете: «Все для хроматографии») */
function withAccent(text: string, accent?: string): ReactNode {
  const at = accent ? text.indexOf(accent) : -1;
  if (!accent || at < 0) return text;
  return (
    <>
      {text.slice(0, at)}
      <span className="text-accent">{accent}</span>
      {text.slice(at + accent.length)}
    </>
  );
}

function Plate({ slide, heading, priority }: { slide: HeroSlide; heading: 'h1' | 'h2' | 'p'; priority: boolean }) {
  const Heading = heading;
  return (
    <div className="relative size-full overflow-hidden rounded-block bg-[linear-gradient(90deg,#0d0d0d_0%,#161c16_137.94%)]">
      <div aria-hidden className="hero-plate-visual pointer-events-none">
        <Visual plate={slide.plate} priority={priority} />
      </div>
      <div className="hero-plate-text">
        <div className="hero-plate-copy">
          <Heading id={heading === 'h1' ? 'hero-title' : undefined} className="hero-plate-title font-medium text-text">
            {withAccent(slide.title, slide.titleAccent)}
          </Heading>
          {slide.subtitle ? <p className="hero-plate-lead text-text">{withAccent(slide.subtitle, slide.subtitleAccent)}</p> : null}
        </div>
        {slide.ctas.length ? (
          <div className="flex flex-wrap gap-[22px]">
            {slide.ctas.map((c) => (
              <Button
                key={c.label}
                href={c.href}
                variant={c.variant}
                size="m"
                className={c.variant === 'secondary' ? 'bg-surface' : undefined}
                icon={c.variant === 'primary' ? <ArrowDownRightIcon size={24} /> : undefined}
              >
                {c.label}
              </Button>
            ))}
          </div>
        ) : null}
      </div>
    </div>
  );
}

function ArrowCircle({ direction }: { direction: 'left' | 'right' }) {
  return (
    <svg aria-hidden viewBox="0 0 86 86" className="size-full">
      <circle cx="43" cy="43" r="43" className="fill-accent transition-colors duration-300 group-hover:fill-accent-hover" />
      <path
        transform={direction === 'left' ? 'rotate(180 43 43)' : undefined}
        d="M42.8846 31.3897C43.5168 30.7487 44.542 30.749 45.1744 31.3897L55.4802 41.8391C56.1126 42.4803 56.1126 43.5197 55.4802 44.1609L45.1744 54.6103C44.542 55.251 43.5168 55.2513 42.8846 54.6103C42.2523 53.9692 42.2527 52.9298 42.8846 52.2885L50.4261 44.6419H31.6647C30.7704 44.6419 30.0454 43.9068 30.0454 43C30.0454 42.0932 30.7704 41.3581 31.6647 41.3581H50.4261L42.8846 33.7115C42.2527 33.0702 42.2523 32.0308 42.8846 31.3897Z"
        fill="#1C1C1C"
      />
    </svg>
  );
}

function useReducedMotion() {
  const [reduced, setReduced] = useState(false);
  useEffect(() => {
    const query = window.matchMedia('(prefers-reduced-motion: reduce)');
    const update = () => setReduced(query.matches);
    update();
    query.addEventListener('change', update);
    return () => query.removeEventListener('change', update);
  }, []);
  return reduced;
}

/**
 * Первый экран по макету Figma «Hero plates» (правки 02.11.2026): плашки на тёмном градиенте, соседние видны по краям,
 * стрелки листают по кругу в обе стороны. По краям ленты — копии двух последних и двух первых плашек: после перехода
 * на копию лента без анимации встаёт на настоящую плашку, поэтому круг бесконечный. Заголовок первой плашки — h1.
 */
export function HeroPlates({ slides }: { slides: HeroSlide[] }) {
  const t = useTranslations('home.hero');
  const n = slides.length;
  const looped = n > 1;
  const offset = looped ? 2 : 0;
  const items = looped
    ? [
        ...[n - 2, n - 1].map((i) => ({ slide: slides[(i + n) % n], copy: true })),
        ...slides.map((slide) => ({ slide, copy: false })),
        ...[0, 1].map((i) => ({ slide: slides[i % n], copy: true })),
      ]
    : slides.map((slide) => ({ slide, copy: false }));

  const [pos, setPos] = useState(offset);
  const [animate, setAnimate] = useState(true);
  const moving = useRef(false);
  const fallback = useRef<number | undefined>(undefined);
  const swipeStart = useRef<number | null>(null);
  const reduced = useReducedMotion();
  const active = looped ? (((pos - offset) % n) + n) % n : 0;

  // С копии — на настоящую плашку, без анимации
  const settle = useCallback(() => {
    window.clearTimeout(fallback.current);
    moving.current = false;
    setPos((p) => {
      if (p >= offset + n) return p - n;
      if (p < offset) return p + n;
      return p;
    });
  }, [n, offset]);

  useEffect(() => {
    if (!animate) {
      // Переход без анимации отрисован — следующий снова анимированный
      const id = window.requestAnimationFrame(() => window.requestAnimationFrame(() => setAnimate(true)));
      return () => window.cancelAnimationFrame(id);
    }
  }, [animate]);

  useEffect(() => () => window.clearTimeout(fallback.current), []);

  const go = useCallback(
    (step: 1 | -1) => {
      if (!looped || moving.current) return;
      if (reduced) {
        setAnimate(false);
        setPos((p) => offset + ((((p - offset + step) % n) + n) % n));
        return;
      }
      moving.current = true;
      setAnimate(true);
      setPos((p) => p + step);
      // Если transitionend не придёт (вкладка свёрнута), лента всё равно встанет на место
      fallback.current = window.setTimeout(() => {
        setAnimate(false);
        settle();
      }, MOVE_MS + 200);
    },
    [looped, n, offset, reduced, settle],
  );

  return (
    <section aria-labelledby="hero-title" className="pt-[88px] lg:pt-[152px]">
      <div
        role="region"
        aria-roledescription="carousel"
        aria-label={t('region')}
        // clip, а не hidden: hidden-блок браузер прокручивает сам при фокусе внутри, и лента съезжает
        className="hero-plates relative touch-pan-y overflow-clip"
        onScroll={(e) => {
          e.currentTarget.scrollLeft = 0;
        }}
        onKeyDown={(e) => {
          if (e.key === 'ArrowRight') go(1);
          if (e.key === 'ArrowLeft') go(-1);
        }}
        onPointerDown={(e) => {
          if (e.pointerType !== 'mouse') swipeStart.current = e.clientX;
        }}
        onPointerUp={(e) => {
          if (swipeStart.current === null) return;
          const dx = e.clientX - swipeStart.current;
          swipeStart.current = null;
          if (Math.abs(dx) > 50) go(dx < 0 ? 1 : -1);
        }}
      >
        <div
          className="flex"
          style={{
            gap: 'var(--gap)',
            transform: `translateX(calc((100cqw - var(--plate-w)) / 2 - ${pos} * (var(--plate-w) + var(--gap))))`,
            transition: animate && !reduced ? `transform ${MOVE_MS}ms cubic-bezier(0.65, 0, 0.35, 1)` : 'none',
          }}
          onTransitionEnd={(e) => {
            if (e.target !== e.currentTarget || e.propertyName !== 'transform') return;
            setAnimate(false);
            settle();
          }}
        >
          {items.map(({ slide, copy }, i) => {
            const real = i - offset;
            const current = !copy && real === active;
            return (
              <div
                key={`${slide.id}-${i}`}
                role={copy ? undefined : 'group'}
                aria-roledescription={copy ? undefined : 'slide'}
                aria-label={copy ? undefined : t('slide', { current: real + 1, total: n })}
                aria-hidden={copy || !current ? true : undefined}
                inert={!current}
                className="shrink-0"
                style={{ width: 'var(--plate-w)', height: 'var(--plate-h)' }}
              >
                <Plate slide={slide} heading={copy ? 'p' : real === 0 ? 'h1' : 'h2'} priority={!copy && real === 0} />
              </div>
            );
          })}
        </div>

        {looped ? (
          <>
            <button type="button" aria-label={t('prev')} onClick={() => go(-1)} className="hero-arrow hero-arrow-prev group">
              <ArrowCircle direction="left" />
            </button>
            <button type="button" aria-label={t('next')} onClick={() => go(1)} className="hero-arrow hero-arrow-next group">
              <ArrowCircle direction="right" />
            </button>
          </>
        ) : null}
      </div>
    </section>
  );
}
