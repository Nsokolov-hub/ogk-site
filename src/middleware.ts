import createMiddleware from 'next-intl/middleware';
import type { NextRequest } from 'next/server';
import { routing } from './i18n/routing';
import { trackAttribution } from './lib/attribution-cookie';

const intl = createMiddleware(routing);

export default function middleware(request: NextRequest) {
  const response = intl(request);
  // Источник визита для заявок (ТЗ 15.3): cookie ogk_attr читает API сайта
  trackAttribution(request, response);
  return response;
}

export const config = {
  // Всё, кроме API, служебных файлов Next, статики и файлов с расширением
  matcher: ['/((?!api|_next|_vercel|files|images|.*\\..*).*)'],
};
