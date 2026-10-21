import createMiddleware from 'next-intl/middleware';
import { routing } from './i18n/routing';

export default createMiddleware(routing);

export const config = {
  // Всё, кроме API, служебных файлов Next, статики и файлов с расширением
  matcher: ['/((?!api|_next|_vercel|files|images|.*\\..*).*)'],
};
