import { z } from 'zod';
import { isValidPhone } from './phone';

/**
 * Общие правила полей форм. Сообщения — ключи из messages/*.json (раздел errors),
 * перевод делает компонент формы.
 */
import rules from './contact-rules.json';

/**
 * E-mail: латиница или кириллица в домене, без двух точек подряд, зона из букв; ловим опечатки в популярных
 * доменах и одноразовые ящики (замечания бизнеса от 31.10.2026). Существование домена проверяет API.
 */
const LOCAL_RE = /^[a-z0-9!#$%&'*+/=?^_`{|}~-]+(?:\.[a-z0-9!#$%&'*+/=?^_`{|}~-]+)*$/i;
const LABEL_RE = /^(?!-)[a-z0-9а-яё-]{1,63}(?<!-)$/i;
const TLD_RE = /^(?:[a-zа-яё]{2,24}|xn--[a-z0-9-]{2,59})$/i;

export function emailProblem(raw: string): 'email' | 'emailTypo' | 'emailDisposable' | null {
  const value = raw.trim();
  const at = value.lastIndexOf('@');
  if (at < 1 || value.length > 254) return 'email';
  const local = value.slice(0, at);
  const domain = value.slice(at + 1).toLowerCase();
  const labels = domain.split('.');
  if (local.length > 64 || !LOCAL_RE.test(local) || labels.length < 2 || domain.length > 253) return 'email';
  if (!labels.every((label) => LABEL_RE.test(label)) || !TLD_RE.test(labels[labels.length - 1])) return 'email';
  if (domain in rules.typoDomains || rules.badTlds.includes(labels[labels.length - 1])) return 'emailTypo';
  if (rules.disposableDomains.some((bad) => domain === bad || domain.endsWith(`.${bad}`))) return 'emailDisposable';
  return null;
}

/** Подсказка «возможно, вы имели в виду …» для опечатки в домене */
export function emailSuggestion(raw: string): string | null {
  const value = raw.trim();
  const at = value.lastIndexOf('@');
  if (at < 1) return null;
  const domain = value.slice(at + 1).toLowerCase();
  const fixed = (rules.typoDomains as Record<string, string>)[domain];
  return fixed ? `${value.slice(0, at)}@${fixed}` : null;
}

export const ATTACHMENT_EXTENSIONS = ['.xlsx', '.csv', '.pdf', '.docx'] as const;
export const ATTACHMENT_MAX_BYTES = 10 * 1024 * 1024;

export function checkAttachment(file: File): 'fileType' | 'fileSize' | null {
  const name = file.name.toLowerCase();
  if (!ATTACHMENT_EXTENSIONS.some((ext) => name.endsWith(ext))) return 'fileType';
  if (file.size > ATTACHMENT_MAX_BYTES) return 'fileSize';
  return null;
}

export const fields = {
  fullName: z.string().trim().min(1, 'required').min(3, 'tooShort'),
  shortName: z.string().trim().min(1, 'required').min(2, 'tooShort'),
  company: z.string().trim().min(1, 'required').min(2, 'tooShort'),
  email: z
    .string()
    .trim()
    .min(1, 'required')
    .superRefine((value, ctx) => {
      const problem = emailProblem(value);
      if (problem) ctx.addIssue({ code: 'custom', message: problem });
    }),
  phone: z.string().trim().min(1, 'required').refine(isValidPhone, 'phone'),
  message: z.string().trim().min(1, 'required').min(10, 'messageShort'),
  consent: z.boolean().refine((v) => v, 'consent'),
  /** Поле-ловушка для ботов */
  website: z.string().optional(),
};

/** ИНН юрлица (10 цифр) или ИП/физлица (12 цифр) с проверкой контрольных разрядов (RFQ-03) */
export function isValidInn(value: string): boolean {
  const d = value.replace(/\s/g, '');
  if (!/^\d{10}$|^\d{12}$/.test(d)) return false;
  const n = d.split('').map(Number);
  const check = (weights: number[]) => (weights.reduce((s, w, i) => s + w * n[i], 0) % 11) % 10;
  if (n.length === 10) return check([2, 4, 10, 3, 5, 9, 4, 6, 8]) === n[9];
  return check([7, 2, 4, 10, 3, 5, 9, 4, 6, 8]) === n[10] && check([3, 7, 2, 4, 10, 3, 5, 9, 4, 6, 8]) === n[11];
}
