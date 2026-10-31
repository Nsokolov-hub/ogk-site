/**
 * Телефон: маска +7 (999) 999-99-99 для российских номеров,
 * свободный международный ввод для остальных, нормализация в E.164.
 */

import rules from './contact-rules.json';

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

/**
 * Номер E.164 (+79991234567) похож на настоящий: длина по коду страны (Россия и Казахстан, СНГ, США), для
 * России и Казахстана — допустимая первая цифра кода, без номеров из одной цифры и подряд идущих цифр.
 * Те же правила проверяет API (замечания бизнеса от 31.10.2026).
 */
export function isPlausibleE164(e164: string): boolean {
  if (!/^\+[1-9]\d{6,14}$/.test(e164)) return false;
  const d = e164.slice(1);
  if (d.length < rules.phoneMinDigits || d.length > rules.phoneMaxDigits) return false;
  const code = Object.keys(rules.phoneLengths)
    .sort((a, b) => b.length - a.length)
    .find((prefix) => d.startsWith(prefix));
  if (code && d.length !== rules.phoneLengths[code as keyof typeof rules.phoneLengths]) return false;
  const national = code ? d.slice(code.length) : d.slice(-10);
  if (code === '7' && !rules.ruFirstDigits.includes(national[0])) return false;
  if (new Set(national).size === 1) return false;
  // 1234567…, 0123456…, 9876543…: набор подряд вместо номера
  if (['1234567', '0123456', '9876543', '7654321'].includes(national.slice(0, 7))) return false;
  return true;
}

/** +79991234567 или null, если номер неполный или не похож на настоящий */
export function toE164(v: string): string | null {
  const t = v.trim();
  let d = digitsOnly(t);
  if (!d) return null;
  if (!t.startsWith('+')) {
    if (d.length === 11 && (d[0] === '8' || d[0] === '7')) d = `7${d.slice(1)}`;
    else if (d.length === 10 && d[0] === '9') d = `7${d}`;
  }
  const e164 = `+${d}`;
  return isPlausibleE164(e164) ? e164 : null;
}

export const isValidPhone = (v: string) => toE164(v) !== null;
