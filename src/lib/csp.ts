/**
 * Content-Security-Policy витрины (NFR-04). Скрипты — только с nonce этого ответа и загруженные ими ('strict-dynamic'):
 * так работают Яндекс Метрика, GA4 и SmartCaptcha без перечня всех их адресов. Вебвизор открывает страницу во фрейме
 * Метрики — поэтому frame-ancestors разрешает её домены.
 */
const METRIKA = ['https://mc.yandex.ru', 'https://mc.yandex.com'];
const GOOGLE = ['https://*.google-analytics.com', 'https://*.analytics.google.com', 'https://*.googletagmanager.com'];
const CAPTCHA = ['https://smartcaptcha.yandexcloud.net'];

export function contentSecurityPolicy(nonce: string, options: { development: boolean; https: boolean }): string {
  const directives: Record<string, string[]> = {
    'default-src': ["'self'"],
    // https: — запасной вариант для браузеров без strict-dynamic, современные его игнорируют
    'script-src': ["'self'", `'nonce-${nonce}'`, "'strict-dynamic'", 'https:', ...(options.development ? ["'unsafe-eval'"] : [])],
    'style-src': ["'self'", "'unsafe-inline'"],
    'img-src': ["'self'", 'data:', 'blob:', ...METRIKA, ...GOOGLE],
    'font-src': ["'self'", 'data:'],
    'connect-src': [
      "'self'",
      ...METRIKA,
      'wss://mc.yandex.ru',
      'wss://mc.yandex.com',
      ...GOOGLE,
      ...CAPTCHA,
      ...(options.development ? ['ws:'] : []),
    ],
    'frame-src': ["'self'", 'blob:', ...METRIKA, ...CAPTCHA],
    'child-src': ["'self'", 'blob:', ...METRIKA],
    'worker-src': ["'self'", 'blob:'],
    'object-src': ["'none'"],
    'base-uri': ["'self'"],
    'form-action': ["'self'"],
    'frame-ancestors': ["'self'", 'https://metrika.yandex.ru', 'https://metrika.yandex.com', 'https://*.webvisor.com'],
  };
  const parts = Object.entries(directives).map(([name, values]) => `${name} ${values.join(' ')}`);
  if (options.https) parts.push('upgrade-insecure-requests');
  return parts.join('; ');
}
