import { defineRouting } from 'next-intl/routing';

export const routing = defineRouting({
  locales: ['ru', 'en'],
  defaultLocale: 'ru',
  // RU без префикса (/), EN — /en/
  localePrefix: 'as-needed',
  // EN-03: язык не определяем по IP/браузеру, только переключателем
  localeDetection: false,
});

export type Locale = (typeof routing.locales)[number];
