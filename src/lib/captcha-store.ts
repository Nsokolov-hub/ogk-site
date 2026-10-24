import { create } from 'zustand';
import { SubmitError } from './submit-error';

/**
 * Яндекс SmartCaptcha по требованию API (RFQ-06): сервер отвечает 428, когда форма заполнена слишком быстро
 * или с адреса много заявок. Окно одно на сайт (CaptchaHost), формы о нём не знают — его открывает
 * submitSiteRequest и ждёт токен.
 */
interface CaptchaState {
  open: boolean;
  lang: 'ru' | 'en';
  pending: { resolve: (token: string) => void; reject: (error: Error) => void } | null;
}

export const useCaptchaStore = create<CaptchaState>(() => ({ open: false, lang: 'ru', pending: null }));

export const captchaSiteKey = () => process.env.NEXT_PUBLIC_SMARTCAPTCHA_SITE_KEY ?? '';

export function requestCaptcha(lang: 'ru' | 'en'): Promise<string> {
  if (!captchaSiteKey()) return Promise.reject(new SubmitError('CAPTCHA_UNAVAILABLE', 428));
  useCaptchaStore.getState().pending?.reject(new SubmitError('CAPTCHA_CANCELLED', 428));
  return new Promise((resolve, reject) => useCaptchaStore.setState({ open: true, lang, pending: { resolve, reject } }));
}

export function solveCaptcha(token: string) {
  useCaptchaStore.getState().pending?.resolve(token);
  useCaptchaStore.setState({ open: false, pending: null });
}

export function cancelCaptcha() {
  useCaptchaStore.getState().pending?.reject(new SubmitError('CAPTCHA_CANCELLED', 428));
  useCaptchaStore.setState({ open: false, pending: null });
}
