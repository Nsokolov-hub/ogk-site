import { useId } from 'react';
import { cn } from '@/lib/cn';

/** Разбивает название на 2 строки по словам; лишнее — в многоточие */
function wrapTwoLines(text: string, max: number): string[] {
  const lines: string[] = [''];
  for (const word of text.split(/\s+/)) {
    const i = lines.length - 1;
    const candidate = lines[i] ? `${lines[i]} ${word}` : word;
    if (candidate.length <= max) {
      lines[i] = candidate;
    } else if (!lines[i]) {
      lines[i] = word.slice(0, max);
      lines.push(word.slice(max));
    } else {
      lines.push(word);
    }
  }
  if (lines.length <= 2 && lines[lines.length - 1].length <= max) return lines;
  const second = lines.slice(1).join(' ');
  return [lines[0], `${second.slice(0, max - 1).trimEnd()}…`];
}

/**
 * Фирменная заглушка флакона ОГК-ХИМ (ТЗ 5.3): когда нет фото производителя и 2D-структуры.
 * На этикетке — бренд, название и CAS.
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
  const [line1, line2] = wrapTwoLines(name, 19);

  return (
    <svg
      viewBox="0 0 200 200"
      role="img"
      aria-label={cas ? `${name}, CAS ${cas}` : name}
      className={cn('h-full w-full', className)}
    >
      <defs>
        <linearGradient id={`${uid}-glass`} x1="0" x2="1" y1="0" y2="0">
          <stop offset="0%" stopColor="#2e1406" />
          <stop offset="30%" stopColor="#7a3f15" />
          <stop offset="55%" stopColor="#8f4c1b" />
          <stop offset="80%" stopColor="#5a2b0c" />
          <stop offset="100%" stopColor="#241004" />
        </linearGradient>
        <linearGradient id={`${uid}-metal`} x1="0" x2="1" y1="0" y2="0">
          <stop offset="0%" stopColor="#7d7d7d" />
          <stop offset="25%" stopColor="#d9d9d9" />
          <stop offset="50%" stopColor="#f2f2f2" />
          <stop offset="75%" stopColor="#a8a8a8" />
          <stop offset="100%" stopColor="#6e6e6e" />
        </linearGradient>
        <linearGradient id={`${uid}-cap`} x1="0" x2="1" y1="0" y2="0">
          <stop offset="0%" stopColor="#4fbf5c" />
          <stop offset="40%" stopColor="#82ee8d" />
          <stop offset="70%" stopColor="#9cf5a5" />
          <stop offset="100%" stopColor="#4aa955" />
        </linearGradient>
        <radialGradient id={`${uid}-glow`} cx="0.5" cy="0.3" r="0.6">
          <stop offset="0%" stopColor="#82ee8d" stopOpacity="0.18" />
          <stop offset="100%" stopColor="#82ee8d" stopOpacity="0" />
        </radialGradient>
      </defs>

      <rect x="0" y="0" width="200" height="200" fill={`url(#${uid}-glow)`} />
      <ellipse cx="100" cy="190" rx="54" ry="5" fill="#000" opacity="0.35" />

      {/* стекло */}
      <rect x="54" y="64" width="92" height="124" rx="14" fill={`url(#${uid}-glass)`} />
      <rect x="70" y="52" width="60" height="16" rx="4" fill="#4a230c" />
      {/* обжимное кольцо и крышка */}
      <rect x="64" y="36" width="72" height="20" rx="4" fill={`url(#${uid}-metal)`} />
      <rect x="60" y="14" width="80" height="25" rx="8" fill={`url(#${uid}-cap)`} />
      <rect x="66" y="17" width="68" height="4" rx="2" fill="#c4ffca" opacity="0.6" />

      {/* этикетка */}
      <rect x="54" y="96" width="92" height="68" fill="#f3f3ef" />
      <rect x="54" y="96" width="92" height="12" fill="#1c1c1c" />
      <text x="60" y="105" fontSize="7" fontWeight="700" fill="#82ee8d" letterSpacing="0.6">
        {(brand ?? 'OGK CHEM').toUpperCase().slice(0, 18)}
      </text>
      <text x="60" y="122" fontSize="8.5" fontWeight="600" fill="#1c1c1c">
        {line1}
      </text>
      {line2 ? (
        <text x="60" y="133" fontSize="8.5" fontWeight="600" fill="#1c1c1c">
          {line2}
        </text>
      ) : null}
      {cas ? (
        <text x="60" y="155" fontSize="7" fill="#4a4a4a">
          CAS {cas}
        </text>
      ) : null}

      {/* блик на стекле */}
      <rect x="61" y="70" width="5" height="110" rx="2.5" fill="#fff" opacity="0.16" />
    </svg>
  );
}
