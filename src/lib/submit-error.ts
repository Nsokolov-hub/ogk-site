/**
 * Ошибка отправки формы с кодом API (backend/app). Формы показывают по коду понятный текст на языке страницы:
 * сообщения сервера только на русском.
 */
export class SubmitError extends Error {
  constructor(
    public code: string,
    public status: number,
    public fields: { field: string; message: string }[] = [],
  ) {
    super(code);
    this.name = 'SubmitError';
  }
}

/** Ключ строки в разделе form сообщений (messages/*.json) для ошибки отправки */
export function submitErrorKey(error: unknown): string {
  const code = error instanceof SubmitError ? error.code : 'NETWORK';
  if (code === 'RATE_LIMITED') return 'errorRate';
  if (code === 'VALIDATION_ERROR') return 'errorFields';
  if (code.startsWith('FILE_')) return 'errorFile';
  if (code.startsWith('CAPTCHA_')) return 'errorCaptcha';
  if (error instanceof SubmitError && error.status >= 500) return 'errorUnavailable';
  return 'errorText';
}
