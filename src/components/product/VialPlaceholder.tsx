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

// Жирное начертание (600) шире обычного примерно на 4 %
const textWidth = (text: string, size: number, spacing = 0, bold = false) =>
  [...text].reduce((w, ch) => w + charEm(ch) * size * (bold ? 1.04 : 1) + spacing, 0);

/** Переносит текст по ширине (длинное слово режет), не больше maxLines строк; лишнее — в многоточие */
function wrapLines(text: string, size: number, maxWidth: number, maxLines = 2): string[] {
  const fits = (s: string) => textWidth(s, size, 0, true) <= maxWidth;
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

/** Бренд на бейдже: длинный сжимается до 6, дальше — многоточие */
function fitBrand(text: string, maxWidth: number) {
  const size = 7.5;
  const spacing = 0.225; // 0.03em из эталона
  if (textWidth(text, size, spacing, true) <= maxWidth) return { text, size, spacing };
  const shrunk = Math.max(6, Math.floor(((size * maxWidth) / textWidth(text, size, spacing, true)) * 100) / 100);
  if (textWidth(text, shrunk, 0, true) <= maxWidth) return { text, size: shrunk, spacing: 0 };
  let cut = text;
  while (cut.length > 1 && textWidth(`${cut}…`, shrunk, 0, true) > maxWidth) cut = cut.slice(0, -1);
  return { text: `${cut.trimEnd()}…`, size: shrunk, spacing: 0 };
}

/** Детерминированный штрихкод из идентификаторов: одинаковый на сервере и в браузере */
function barcode(seed: string, from: number, to: number) {
  let h = 2166136261;
  for (const ch of seed) h = Math.imul(h ^ ch.charCodeAt(0), 16777619);
  const next = () => {
    h = Math.imul(h ^ (h >>> 15), 2246822519);
    h = Math.imul(h ^ (h >>> 13), 3266489917);
    return ((h ^= h >>> 16) >>> 0) / 4294967296;
  };
  // Высоты штрихов и шаг — как в эталоне: 1–2,5 при шаге около 3
  const HEIGHTS = [1, 1.2, 1.8, 2, 2.2, 2.5];
  const bars: { y: number; h: number }[] = [];
  let y = from;
  while (y < to) {
    const bh = HEIGHTS[Math.floor(next() * HEIGHTS.length)];
    bars.push({ y, h: Math.min(bh, to - y + 1) });
    y += bh + 1.8 + Math.round(next()) * 0.4;
  }
  return bars;
}

// Геометрия эталона (viewBox 240 × 260): этикетка, текст и штрихкод
const LABEL = { x: 65, y: 124, w: 110, h: 84, r: 5 };
const TEXT_X = 71;
const NAME_SIZE = 10.5;
const NAME_MIN = 8.5;
const NAME_WIDTH = 90; // от 71 до штрихкода на 166 с запасом
const BAR = { x: 166, w: 6, top: 148, bottom: 194 };

/**
 * Фирменная заглушка флакона ОГК-ХИМ (ТЗ 5.3): когда нет фото производителя и 2D-структуры.
 * Разметка — по эталону заказчика: матовая тёмно-зелёная ребристая крышка, янтарное стекло,
 * этикетка из тёплой матовой бумаги с отступом от края стекла и цилиндрической светотенью,
 * тёмная шапка с оранжевым бейджем бренда, название, CAS и штрихкод. Свечение фона — внутри SVG.
 */
export function VialPlaceholder({
  name,
  cas,
  brand,
  code,
  className,
}: {
  name: string;
  cas?: string;
  brand?: string;
  /** Каталожный номер — из него строится штрихкод */
  code?: string;
  className?: string;
}) {
  const uid = useId().replace(/[^a-zA-Z0-9_-]/g, '');
  const id = (s: string) => `${uid}-${s}`;
  const url = (s: string) => `url(#${id(s)})`;

  // Длинное слово («Hydrochlorothiazide») не рвём, а уменьшаем шрифт
  const longestWord = Math.max(...name.split(/\s+/).map((w) => textWidth(w, NAME_SIZE, 0, true)));
  const nameSize = longestWord > NAME_WIDTH ? Math.max(NAME_MIN, (NAME_SIZE * NAME_WIDTH) / longestWord) : NAME_SIZE;
  const lineHeight = nameSize * 1.22;
  // Без CAS на этикетке есть место под третью строку названия
  const nameLines = wrapLines(name, nameSize, NAME_WIDTH, cas ? 2 : 3);
  const brandLine = fitBrand((brand ?? 'OGK-CHEM').toUpperCase(), 88);
  const badgeW = Math.max(32, textWidth(brandLine.text, brandLine.size, brandLine.spacing, true) + 6);
  const bars = barcode(`${code ?? ''}|${cas ?? ''}|${name}`, BAR.top, BAR.bottom);

  return (
    <svg
      viewBox="0 0 240 260"
      fill="none"
      role="img"
      aria-label={cas ? `${name}, CAS ${cas}` : name}
      className={cn('h-full w-full', className)}
    >
      <defs>
        {/* Свечение на фоне */}
        <radialGradient id={id('bgGlow')} cx="50%" cy="50%" r="50%">
          <stop offset="0%" stopColor="#2E5C3A" stopOpacity="0.45" />
          <stop offset="100%" stopColor="#141714" stopOpacity="0" />
        </radialGradient>
        {/* Тень под дном банки */}
        <radialGradient id={id('floorShadow')} cx="50%" cy="50%" r="50%">
          <stop offset="0%" stopColor="#000000" stopOpacity="0.85" />
          <stop offset="60%" stopColor="#000000" stopOpacity="0.4" />
          <stop offset="100%" stopColor="#000000" stopOpacity="0" />
        </radialGradient>
        {/* Матовая тёмно-зелёная крышка (цилиндрический градиент) */}
        <linearGradient id={id('capGrad')} x1="68" y1="0" x2="172" y2="0" gradientUnits="userSpaceOnUse">
          <stop offset="0%" stopColor="#122416" />
          <stop offset="22%" stopColor="#294A30" />
          <stop offset="45%" stopColor="#355B3D" />
          <stop offset="75%" stopColor="#1A3220" />
          <stop offset="100%" stopColor="#0E1C11" />
        </linearGradient>
        {/* Янтарное стекло корпуса */}
        <linearGradient id={id('glassBody')} x1="62" y1="0" x2="178" y2="0" gradientUnits="userSpaceOnUse">
          <stop offset="0%" stopColor="#1E0901" />
          <stop offset="18%" stopColor="#5A2006" />
          <stop offset="38%" stopColor="#8C380F" />
          <stop offset="65%" stopColor="#4A1804" />
          <stop offset="88%" stopColor="#2B0D02" />
          <stop offset="100%" stopColor="#160600" />
        </linearGradient>
        {/* Блик стекла слева */}
        <linearGradient id={id('glassHighlight')} x1="0" y1="0" x2="1" y2="0">
          <stop offset="0%" stopColor="#FFFFFF" stopOpacity="0.22" />
          <stop offset="100%" stopColor="#FFFFFF" stopOpacity="0" />
        </linearGradient>
        {/* Цилиндрическая светотень для матовой этикетки */}
        <linearGradient id={id('labelShade')} x1="65" y1="0" x2="175" y2="0" gradientUnits="userSpaceOnUse">
          <stop offset="0%" stopColor="#000000" stopOpacity="0.28" />
          <stop offset="14%" stopColor="#000000" stopOpacity="0.04" />
          <stop offset="35%" stopColor="#FFFFFF" stopOpacity="0.08" />
          <stop offset="72%" stopColor="#000000" stopOpacity="0.08" />
          <stop offset="90%" stopColor="#000000" stopOpacity="0.25" />
          <stop offset="100%" stopColor="#000000" stopOpacity="0.45" />
        </linearGradient>
        {/* Рёбра на крышке */}
        <pattern id={id('capRibs')} width="6" height="46" patternUnits="userSpaceOnUse">
          <rect x="0" y="0" width="2" height="46" fill="#000000" fillOpacity="0.22" />
          <rect x="2" y="0" width="1.5" height="46" fill="#FFFFFF" fillOpacity="0.06" />
        </pattern>
        {/* Текст не выходит за этикетку, даже если оценка ширины ошиблась */}
        <clipPath id={id('labelClip')}>
          <rect x={LABEL.x} y={LABEL.y} width={LABEL.w} height={LABEL.h} rx={LABEL.r} />
        </clipPath>
      </defs>

      {/* Фоновое свечение */}
      <circle cx="120" cy="135" r="95" fill={url('bgGlow')} />

      {/* Контактная тень на полу */}
      <ellipse cx="120" cy="236" rx="68" ry="10" fill={url('floorShadow')} />

      {/* Горловина: тёмное янтарное стекло под крышкой */}
      <rect x="76" y="76" width="88" height="18" rx="3" fill={url('glassBody')} />
      <rect x="76" y="76" width="88" height="6" fill="#000000" fillOpacity="0.5" />
      <path d="M76 84 H164" stroke="#A84B18" strokeWidth="1" strokeOpacity="0.5" />

      {/* Корпус стеклянной банки */}
      <path
        d="M62 114 C62 98, 76 92, 80 90 H160 C164 92, 178 98, 178 114 V218 C178 229, 170 235, 158 235 H82 C70 235, 62 229, 62 218 Z"
        fill={url('glassBody')}
      />

      {/* Янтарные рефлексы на плечиках и дне */}
      <ellipse cx="120" cy="105" rx="46" ry="8" fill="#B84B14" fillOpacity="0.25" />
      <ellipse cx="120" cy="228" rx="48" ry="5" fill="#B84B14" fillOpacity="0.3" />
      <path d="M66 220 C85 226, 155 226, 174 220" stroke="#FF8A47" strokeOpacity="0.2" strokeWidth="1.5" fill="none" />

      {/* Этикетка */}
      <g>
        {/* Тень от этикетки на стекле */}
        <rect x="64" y="125" width="112" height="86" rx="5" fill="#000000" fillOpacity="0.45" />
        {/* Основа: тёплая матовая бумага */}
        <rect x={LABEL.x} y={LABEL.y} width={LABEL.w} height={LABEL.h} rx={LABEL.r} fill="#EAE7DF" />
        {/* Тёмная шапка этикетки */}
        <path d="M65 129 C65 126.2, 67.2 124, 70 124 H170 C172.8 124, 175 126.2, 175 129 V142 H65 Z" fill="#1A1A1A" />

        <g clipPath={url('labelClip')}>
          {/* Оранжевый бейдж бренда */}
          <rect x="71" y="127.5" width={badgeW} height="11" rx="2" fill="#C86428" />
          <text
            x="74"
            y="135.5"
            fill="#FFFFFF"
            fontSize={brandLine.size}
            fontWeight="600"
            letterSpacing={brandLine.spacing}
          >
            {brandLine.text}
          </text>

          {/* Название */}
          {nameLines.map((line, i) => (
            <text key={i} x={TEXT_X} y={158 + i * lineHeight} fill="#181818" fontSize={nameSize} fontWeight="600">
              {line}
            </text>
          ))}

          {/* CAS внизу этикетки */}
          {cas ? (
            <text x={TEXT_X} y="198" fill="#3A3A3A" fontSize="8" fontWeight="500">
              CAS {cas}
            </text>
          ) : null}

          {/* Штрихкод справа */}
          <g fill="#222222" opacity="0.75">
            {bars.map((b, i) => (
              <rect key={i} x={BAR.x} y={b.y} width={BAR.w} height={b.h} />
            ))}
          </g>
        </g>

        {/* Главный слой: цилиндрическое затенение поверх всей этикетки */}
        <rect x={LABEL.x} y={LABEL.y} width={LABEL.w} height={LABEL.h} rx={LABEL.r} fill={url('labelShade')} />
      </g>

      {/* Продольные блики стекла */}
      <rect x="68" y="98" width="12" height="128" rx="6" fill={url('glassHighlight')} />
      <rect x="164" y="100" width="4" height="124" rx="2" fill="#FFFFFF" fillOpacity="0.06" />

      {/* Крышка */}
      <g>
        <rect x="68" y="32" width="104" height="44" rx="6" fill={url('capGrad')} />
        <rect x="70" y="34" width="100" height="36" rx="3" fill={url('capRibs')} />
        <rect x="67" y="70" width="106" height="7" rx="2.5" fill={url('capGrad')} />
        <path d="M68 70 H172" stroke="#0B160D" strokeWidth="1" />
        <path d="M74 33.5 H166" stroke="#FFFFFF" strokeOpacity="0.18" strokeWidth="1.2" strokeLinecap="round" />
      </g>
    </svg>
  );
}
