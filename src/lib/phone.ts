/**
 * Телефон: маска +7 (999) 999-99-99 для российских номеров,
 * свободный международный ввод для остальных, нормализация в E.164.
 */

export const digitsOnly = (v: string) => v.replace(/\D/g, '');

/** Форматирует то, что ввёл пользователь, для показа в поле */
export function formatPhoneInput(raw: string): string {
  const t = raw.trimStart();
  if (t === '') return '';
  if (t === '+') return '+';

  let d = digitsOnly(t);
  const international = t.startsWith('+') && !t.startsWith('+7');
  if (international) return `+${d.slice(0, 15)}`;

  if (d.startsWith('8')) d = `7${d.slice(1)}`;
  else if (d.startsWith('9')) d = `7${d}`;
  else if (!d.startsWith('7')) return `+${d.slice(0, 15)}`;

  const n = d.slice(1, 11);
  let out = '+7';
  if (n.length > 0) out += ` (${n.slice(0, 3)}`;
  if (n.length >= 3) out += ')';
  if (n.length > 3) out += ` ${n.slice(3, 6)}`;
  if (n.length > 6) out += `-${n.slice(6, 8)}`;
  if (n.length > 8) out += `-${n.slice(8, 10)}`;
  return out;
}

/** +79991234567 или null, если номер неполный */
export function toE164(v: string): string | null {
  const t = v.trim();
  let d = digitsOnly(t);
  if (!d) return null;
  if (!t.startsWith('+')) {
    if (d.length === 11 && (d[0] === '8' || d[0] === '7')) d = `7${d.slice(1)}`;
    else if (d.length === 10 && d[0] === '9') d = `7${d}`;
  }
  if (d.startsWith('7') && d.length !== 11) return null;
  if (d.length < 10 || d.length > 15) return null;
  return `+${d}`;
}

export const isValidPhone = (v: string) => toE164(v) !== null;
