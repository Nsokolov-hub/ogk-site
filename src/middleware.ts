import createMiddleware from 'next-intl/middleware';
import type { NextRequest } from 'next/server';
import { routing } from './i18n/routing';
import { trackAttribution } from './lib/attribution-cookie';
import { contentSecurityPolicy } from './lib/csp';

const intl = createMiddleware(routing);

export default function middleware(request: NextRequest) {
  // CSP с одноразовым nonce (NFR-04): Next ставит его своим скриптам, счётчики берут его из заголовка x-nonce.
  // next-intl переносит заголовки запроса в ответ рендера, поэтому их достаточно поставить здесь
  const nonce = btoa(crypto.randomUUID());
  const policy = contentSecurityPolicy(nonce, {
    development: process.env.NODE_ENV !== 'production',
    https: request.headers.get('x-forwarded-proto') === 'https',
  });
  request.headers.set('x-nonce', nonce);
  request.headers.set('Content-Security-Policy', policy);
  const response = intl(request);
  response.headers.set('Content-Security-Policy', policy);
  // Источник визита для заявок (ТЗ 15.3): cookie ogk_attr читает API сайта
  trackAttribution(request, response);
  return response;
}

export const config = {
  // Всё, кроме API, служебных файлов Next, статики и файлов с расширением
  matcher: ['/((?!api|_next|_vercel|files|images|.*\\..*).*)'],
};
