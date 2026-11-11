import { defineRouting } from 'next-intl/routing';

export const routing = defineRouting({
  locales: ['ru', 'en'],
  defaultLocale: 'ru',
  // RU без префикса (/), EN — /en/
  localePrefix: 'as-needed',
  // EN-03: язык не определяем по IP/браузеру, только переключателем
  localeDetection: false,
  // hreflang ставит только <head> страницы и только при наличии перевода (lib/seo, EN-02). Заголовок Link от next-intl
  // объявлял английскую пару у каждой страницы, в том числе у закрытых noindex (аудит 11.11.2026)
  alternateLinks: false,
});

export type Locale = (typeof routing.locales)[number];
