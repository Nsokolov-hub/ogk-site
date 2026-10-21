import { z } from 'zod';
import { isValidPhone } from './phone';

/**
 * Общие правила полей форм. Сообщения — ключи из messages/*.json (раздел errors),
 * перевод делает компонент формы.
 */
const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/;

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
  email: z.string().trim().min(1, 'required').regex(EMAIL_RE, 'email'),
  phone: z.string().trim().min(1, 'required').refine(isValidPhone, 'phone'),
  message: z.string().trim().min(1, 'required').min(10, 'messageShort'),
  consent: z.boolean().refine((v) => v, 'consent'),
  /** Поле-ловушка для ботов */
  website: z.string().optional(),
};
