/** Согласие на cookies (152-ФЗ, NFR-06). Счётчики аналитики грузим только при значении 'all'. */
export type CookieConsent = 'all' | 'necessary';

const KEY = 'ogk-cookie-consent';
export const CONSENT_EVENT = 'ogk:cookie-consent';

export function getCookieConsent(): CookieConsent | null {
  try {
    const v = window.localStorage.getItem(KEY);
    return v === 'all' || v === 'necessary' ? v : null;
  } catch {
    return null;
  }
}

export function setCookieConsent(value: CookieConsent) {
  try {
    window.localStorage.setItem(KEY, value);
  } catch {
    // приватный режим или запрет хранилища — баннер покажется снова, это допустимо
  }
  window.dispatchEvent(new CustomEvent(CONSENT_EVENT, { detail: value }));
}

export function hasAnalyticsConsent(): boolean {
  if (typeof window === 'undefined') return false;
  return getCookieConsent() === 'all';
}
