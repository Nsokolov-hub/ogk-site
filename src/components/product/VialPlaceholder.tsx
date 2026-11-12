import { cn } from '@/lib/cn';
import type { PackKind } from '@/lib/pack-kind';

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
 * Тара — по два файла на вид на весь сайт: всё, что под текстом этикетки, и всё, что поверх него. Рамка этикетки
 * у каждой тары своя (те же числа, что в scripts/draw-packaging.py), с пропорцией эталона 110 × 84: текст ниже
 * свёрстан в координатах эталона и масштабируется в рамку целиком.
 */
const PACKS: Record<PackKind, { base: string; top: string; label: { x: number; y: number; w: number; h: number } }> = {
  vial: { base: '/images/products/vial-base.svg', top: '/images/products/vial-top.svg', label: LABEL },
  bottle: pack('bottle', 70, 136, 100),
  jar: pack('jar', 65, 132, 110),
  solvent: pack('solvent', 78, 140, 84),
  tube: pack('tube', 85, 98, 70),
  box: pack('box', 62, 132, 110),
};

function pack(kind: PackKind, x: number, y: number, w: number) {
  const files = `/images/products/pack-${kind}`;
  return { base: `${files}-base.svg`, top: `${files}-top.svg`, label: { x, y, w, h: Math.round(((w * 84) / 110) * 100) / 100 } };
}

/**
 * Фирменная заглушка флакона ОГК-ХИМ (ТЗ 5.3): когда нет фото производителя и 2D-структуры.
 * Рисунок — по эталону заказчика: матовая тёмно-зелёная ребристая крышка, янтарное стекло,
 * этикетка из тёплой матовой бумаги с отступом от края стекла и цилиндрической светотенью,
 * тёмная шапка с оранжевым бейджем бренда, название, CAS и штрихкод.
 *
 * Банка одна на все товары, меняется только текст этикетки. Поэтому сама банка лежит в двух файлах (BASE — стекло
 * и бумага этикетки, TOP — светотень этикетки, блики и крышка), а в разметке карточки остаются только бейдж,
 * название, CAS и штрихкод (аудит 12.11.2026: целая банка в каждой карточке давала ~145 КБ на странице раздела).
 * Вложенный svg с размерами этикетки обрезает текст по её краям, даже если оценка ширины ошиблась.
 */
export function VialPlaceholder({
  name,
  cas,
  brand,
  code,
  kind = 'vial',
  className,
}: {
  name: string;
  cas?: string;
  brand?: string;
  /** Каталожный номер — из него строится штрихкод */
  code?: string;
  /** Тара по разделу и фасовке (lib/pack-kind); по умолчанию — банка эталона */
  kind?: PackKind;
  className?: string;
}) {
  const art = PACKS[kind];
  // Длинное слово («Hydrochlorothiazide») не рвём, а уменьшаем шрифт
  const longestWord = Math.max(...name.split(/\s+/).map((w) => textWidth(w, NAME_SIZE, 0, true)));
  const nameSize = longestWord > NAME_WIDTH ? Math.max(NAME_MIN, (NAME_SIZE * NAME_WIDTH) / longestWord) : NAME_SIZE;
  const lineHeight = nameSize * 1.22;
  // Без CAS на этикетке есть место под третью строку названия
  const nameLines = wrapLines(name, nameSize, NAME_WIDTH, cas ? 2 : 3);
  const brandLine = fitBrand((brand ?? 'OGK-CHEM').toUpperCase(), 88);
  const badgeW = Math.max(32, textWidth(brandLine.text, brandLine.size, brandLine.spacing, true) + 6);
  const round = (n: number) => Math.round(n * 100) / 100;
  // Штрихкод — одним контуром: прямоугольники штрихов подряд
  const bars = barcode(`${code ?? ''}|${cas ?? ''}|${name}`, BAR.top, BAR.bottom)
    .map((b) => `M${BAR.x} ${round(b.y)}h${BAR.w}v${round(b.h)}h-${BAR.w}z`)
    .join('');

  return (
    <svg
      viewBox="0 0 240 260"
      fill="none"
      role="img"
      aria-label={cas ? `${name}, CAS ${cas}` : name}
      className={cn('h-full w-full', className)}
    >
      <image href={art.base} width="240" height="260" />
      <svg x={art.label.x} y={art.label.y} width={art.label.w} height={art.label.h} viewBox={`${LABEL.x} ${LABEL.y} ${LABEL.w} ${LABEL.h}`}>
        {/* Оранжевый бейдж бренда */}
        <rect x="71" y="127.5" width={round(badgeW)} height="11" rx="2" fill="#C86428" />
        <text x="74" y="135.5" fill="#FFFFFF" fontSize={brandLine.size} fontWeight="600" letterSpacing={brandLine.spacing}>
          {brandLine.text}
        </text>
        {/* Название */}
        {nameLines.map((line, i) => (
          <text key={i} x={TEXT_X} y={round(158 + i * lineHeight)} fill="#181818" fontSize={round(nameSize)} fontWeight="600">
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
        <path d={bars} fill="#222222" opacity="0.75" />
      </svg>
      <image href={art.top} width="240" height="260" />
    </svg>
  );
}
