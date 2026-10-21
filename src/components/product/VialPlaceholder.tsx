import { useId } from 'react';
import { cn } from '@/lib/cn';

// Ширина текста в SVG заранее неизвестна (рендер на сервере), поэтому оцениваем её по классам символов.
// Коэффициенты сняты с Manrope с небольшим запасом; на случай ошибки этикетка ещё и обрезается clipPath.
const NARROW = new Set("iIjl.,:;!|'");
const SEMI = new Set('frt()[]{}-/*1"');
const SLIM = new Set('acesvxyzkJ');
const WIDE = new Set('mwMW%#@');

function charEm(ch: string) {
  if (ch === ' ') return 0.2;
  if (NARROW.has(ch)) return 0.27;
  if (SEMI.has(ch)) return 0.42;
  if (SLIM.has(ch)) return 0.56;
  if (WIDE.has(ch)) return 0.88;
  if (/[A-Z]/.test(ch)) return 0.67;
  if (/[А-ЯЁ]/.test(ch)) return 0.68;
  return 0.6;
}

const textWidth = (text: string, size: number, spacing = 0) =>
  [...text].reduce((w, ch) => w + charEm(ch) * size + spacing, 0);

/** Переносит текст по ширине (длинное слово режет), не больше maxLines строк; лишнее — в многоточие */
function wrapLines(text: string, size: number, maxWidth: number, maxLines = 2): string[] {
  const fits = (s: string) => textWidth(s, size) <= maxWidth;
  // glue — чем строка соединяется с предыдущей: пробел или ничего (кусок разрезанного слова)
  const lines: { text: string; glue: string }[] = [];
  let cur = { text: '', glue: '' };
  for (const word of text.split(/\s+/).filter(Boolean)) {
    const candidate = cur.text ? `${cur.text} ${word}` : word;
    if (fits(candidate)) {
      cur.text = candidate;
      continue;
    }
    if (cur.text) lines.push(cur);
    cur = { text: word, glue: lines.length ? ' ' : '' };
    while (!fits(cur.text)) {
      let n = cur.text.length - 1;
      while (n > 1 && !fits(cur.text.slice(0, n))) n--;
      // химические названия лучше рвать после дефиса или запятой
      const soft = Math.max(cur.text.lastIndexOf('-', n - 1), cur.text.lastIndexOf(',', n - 1));
      if (soft > n / 2) n = soft + 1;
      lines.push({ text: cur.text.slice(0, n), glue: cur.glue });
      cur = { text: cur.text.slice(n), glue: '' };
    }
  }
  if (cur.text) lines.push(cur);
  if (lines.length <= maxLines) return lines.map((l) => l.text);

  let last = lines
    .slice(maxLines - 1)
    .map((l, i) => (i ? l.glue : '') + l.text)
    .join('');
  while (last.length > 1 && !fits(`${last}…`)) last = last.slice(0, -1);
  return [...lines.slice(0, maxLines - 1).map((l) => l.text), `${last.replace(/[\s,(–-]+$/, '')}…`];
}

/** Бренд в одну строку: длинный сжимается до minSize, дальше — многоточие */
function fitBrand(text: string, maxWidth: number) {
  const size = 6.6;
  const spacing = 0.5;
  if (textWidth(text, size, spacing) <= maxWidth) return { text, size, spacing };
  // floor — чтобы ширина после уменьшения не превысила предел на погрешность округления
  const shrunk = Math.max(5.2, Math.floor(((size * maxWidth) / textWidth(text, size)) * 100) / 100);
  if (textWidth(text, shrunk) <= maxWidth) return { text, size: shrunk, spacing: 0 };
  let cut = text;
  while (cut.length > 1 && textWidth(`${cut}…`, shrunk) > maxWidth) cut = cut.slice(0, -1);
  return { text: `${cut.trimEnd()}…`, size: shrunk, spacing: 0 };
}

// Контур банки: горлышко, плечи, корпус со скруглённым дном
const BODY = 'M69 50H131V57C131 61 143 62 143 73V172Q143 185 130 185H70Q57 185 57 172V73C57 62 69 61 69 57Z';
const CAP = 'M64 28Q64 19 73 19H127Q136 19 136 28V48Q136 51 133 51H67Q64 51 64 48Z';
const LABEL = { x: 57, width: 86, top: 94, band: 13, bottom: 160 };
const TEXT_X = 64;
const TEXT_WIDTH = 72;
const NAME_SIZE = 7.6;

/**
 * Фирменная заглушка банки ОГК-ХИМ (ТЗ 5.3): когда нет фото производителя и 2D-структуры.
 * Янтарное стекло, тёмно-зелёная крышка, на этикетке — бренд, название и CAS.
 * Фон прозрачный: банка стоит на ровной плитке карточки, как экспонат в каталоге образцов.
 */
export function VialPlaceholder({
  name,
  cas,
  brand,
  className,
}: {
  name: string;
  cas?: string;
  brand?: string;
  className?: string;
}) {
  const uid = useId().replace(/[^a-zA-Z0-9_-]/g, '');
  const id = (s: string) => `${uid}-${s}`;
  const url = (s: string) => `url(#${id(s)})`;
  // Длинное слово («Hydrochlorothiazide») не рвём, а чуть уменьшаем шрифт
  const longestWord = Math.max(...name.split(/\s+/).map((w) => textWidth(w, NAME_SIZE)));
  const nameSize = longestWord > TEXT_WIDTH ? Math.max(6.6, (NAME_SIZE * TEXT_WIDTH) / longestWord) : NAME_SIZE;
  // Без CAS на этикетке есть место под третью строку названия
  const nameLines = wrapLines(name, nameSize, TEXT_WIDTH, cas ? 2 : 3);
  const brandLine = fitBrand((brand ?? 'OGK CHEM').toUpperCase(), TEXT_WIDTH);
  const bandBottom = LABEL.top + LABEL.band;

  return (
    <svg
      viewBox="0 0 200 200"
      role="img"
      aria-label={cas ? `${name}, CAS ${cas}` : name}
      className={cn('h-full w-full', className)}
    >
      <defs>
        <radialGradient id={id('contact')} cx="0.5" cy="0.5" r="0.5">
          <stop offset="0%" stopColor="#000" stopOpacity="0.6" />
          <stop offset="100%" stopColor="#000" stopOpacity="0" />
        </radialGradient>
        {/* стекло: тёмные края, тёплая середина */}
        <linearGradient id={id('glass')} x1="0" x2="1" y1="0" y2="0">
          <stop offset="0%" stopColor="#1c0b03" />
          <stop offset="9%" stopColor="#3d1b08" />
          <stop offset="24%" stopColor="#6c3411" />
          <stop offset="44%" stopColor="#8a4519" />
          <stop offset="56%" stopColor="#8e481b" />
          <stop offset="74%" stopColor="#683110" />
          <stop offset="91%" stopColor="#371705" />
          <stop offset="100%" stopColor="#170902" />
        </linearGradient>
        <linearGradient id={id('depth')} x1="0" x2="0" y1="0" y2="1">
          <stop offset="0%" stopColor="#000" stopOpacity="0.15" />
          <stop offset="12%" stopColor="#000" stopOpacity="0" />
          <stop offset="82%" stopColor="#000" stopOpacity="0" />
          <stop offset="100%" stopColor="#000" stopOpacity="0.5" />
        </linearGradient>
        <radialGradient id={id('warm')} cx="0.5" cy="0.5" r="0.5">
          <stop offset="0%" stopColor="#c8743a" stopOpacity="0.2" />
          <stop offset="100%" stopColor="#d07a3c" stopOpacity="0" />
        </radialGradient>
        {/* крышка */}
        <linearGradient id={id('cap')} x1="0" x2="1" y1="0" y2="0">
          <stop offset="0%" stopColor="#0b1a10" />
          <stop offset="10%" stopColor="#183221" />
          <stop offset="30%" stopColor="#274b33" />
          <stop offset="48%" stopColor="#2f5c3d" />
          <stop offset="63%" stopColor="#2a5237" />
          <stop offset="84%" stopColor="#183221" />
          <stop offset="100%" stopColor="#0a170e" />
        </linearGradient>
        <linearGradient id={id('capShade')} x1="0" x2="0" y1="0" y2="1">
          <stop offset="0%" stopColor="#fff" stopOpacity="0.1" />
          <stop offset="30%" stopColor="#fff" stopOpacity="0" />
          <stop offset="85%" stopColor="#000" stopOpacity="0.1" />
          <stop offset="100%" stopColor="#000" stopOpacity="0.35" />
        </linearGradient>
        {/* этикетка: светлее в центре, темнее к краям — читается как цилиндр */}
        <linearGradient id={id('paper')} x1="0" x2="1" y1="0" y2="0">
          <stop offset="0%" stopColor="#9f9e96" />
          <stop offset="6%" stopColor="#d6d5cc" />
          <stop offset="18%" stopColor="#ebeae2" />
          <stop offset="50%" stopColor="#f3f2eb" />
          <stop offset="82%" stopColor="#e7e6dd" />
          <stop offset="94%" stopColor="#cccbc2" />
          <stop offset="100%" stopColor="#9c9b93" />
        </linearGradient>
        <linearGradient id={id('band')} x1="0" x2="1" y1="0" y2="0">
          <stop offset="0%" stopColor="#040404" />
          <stop offset="14%" stopColor="#1b1b1b" />
          <stop offset="50%" stopColor="#252525" />
          <stop offset="86%" stopColor="#1a1a1a" />
          <stop offset="100%" stopColor="#030303" />
        </linearGradient>
        <clipPath id={id('labelClip')}>
          <rect x={LABEL.x} y={LABEL.top} width={LABEL.width} height={LABEL.bottom - LABEL.top} />
        </clipPath>
      </defs>

      <ellipse cx="100" cy="187" rx="50" ry="5" fill={url('contact')} />

      {/* стекло */}
      <path d={BODY} fill={url('glass')} />
      <ellipse cx="100" cy="77" rx="34" ry="14" fill={url('warm')} />
      <path d={BODY} fill={url('depth')} />
      <path d="M62 178Q100 183 138 178" fill="none" stroke="#c06a2e" strokeOpacity="0.22" strokeWidth="1" />
      {/* венчик горлышка */}
      <rect x="67" y="49" width="66" height="5" rx="2" fill="#3a1907" />
      <rect x="67" y="53.5" width="66" height="1" fill="#000" opacity="0.35" />

      {/* крышка */}
      <path d={CAP} fill={url('cap')} />
      <path d={CAP} fill={url('capShade')} />
      <path d="M71 20.6H129" stroke="#6fae7f" strokeOpacity="0.55" strokeWidth="1.1" strokeLinecap="round" />
      <rect x="64" y="47.6" width="72" height="1" fill="#000" opacity="0.3" />

      {/* этикетка */}
      <g clipPath={url('labelClip')}>
        <rect x={LABEL.x} y={LABEL.top} width={LABEL.width} height={LABEL.band} fill={url('band')} />
        <rect x={LABEL.x} y={bandBottom} width={LABEL.width} height={LABEL.bottom - bandBottom} fill={url('paper')} />
        <text
          x={TEXT_X}
          y={LABEL.top + 6.5 + brandLine.size * 0.41}
          fontSize={brandLine.size}
          fontWeight="600"
          letterSpacing={brandLine.spacing}
          fill="#7fdf8a"
        >
          {brandLine.text}
        </text>
        {nameLines.map((line, i) => (
          <text key={i} x={TEXT_X} y={bandBottom + 14 + i * 10.5} fontSize={nameSize} fontWeight="500" fill="#262626">
            {line}
          </text>
        ))}
        {cas ? (
          <text x={TEXT_X} y={LABEL.bottom - 8} fontSize="6.2" fontWeight="500" fill="#4f4f4f">
            CAS {cas}
          </text>
        ) : null}
      </g>

      {/* блики на стекле */}
      <path d="M61.5 73C62 67 67 63.5 74 62.5" fill="none" stroke="#fff" strokeOpacity="0.2" strokeWidth="1.4" strokeLinecap="round" />
      <rect x="61.5" y="76" width="3.5" height="96" rx="1.75" fill="#fff" opacity="0.09" />
      <rect x="136.5" y="78" width="1.8" height="90" rx="0.9" fill="#ffb877" opacity="0.12" />
    </svg>
  );
}
