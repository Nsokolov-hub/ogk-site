import { getSite } from '@/lib/content';
import { SITE_URL } from '@/lib/seo';

/**
 * robots.txt (ТЗ SEO-03): закрываем служебные разделы, поиск, корзину и кабинет (и их /en/-версии);
 * Clean-param для Яндекса убирает UTM и метки рекламы. CSS, JS, каталог, бренды, услуги и статьи открыты.
 * Staging (SITE_ENV=staging) закрыт целиком (ТЗ 12.3).
 */
/** Читаем SITE_ENV при запросе, а не при сборке: один образ для staging и production */
export const dynamic = 'force-dynamic';

const CLOSED = ['/admin/', '/api/', '/internal/', '/search/', '/rfq/', '/account/', '/unsubscribe/'];

export async function GET() {
  if (process.env.SITE_ENV === 'staging') {
    return new Response('User-agent: *\nDisallow: /\n', { headers: { 'Content-Type': 'text/plain; charset=utf-8' } });
  }
  // Дополнение из админки (ADM-07) — в обе группы: проверено на синтаксис и на то, что основные разделы открыты
  const extra = await extraRules();
  const disallow = [
    ...[...CLOSED, ...CLOSED.filter((p) => !['/admin/', '/api/', '/internal/'].includes(p)).map((p) => `/en${p}`)].map((p) => `Disallow: ${p}`),
    ...extra,
  ].join('\n');
  const body = [
    'User-agent: *',
    disallow,
    'Allow: /',
    '',
    'User-agent: Yandex',
    disallow,
    'Allow: /',
    'Clean-param: utm_source&utm_medium&utm_campaign&utm_content&utm_term&yclid&gclid',
    '',
    `Sitemap: ${SITE_URL}/sitemap.xml`,
    '',
  ].join('\n');
  return new Response(body, { headers: { 'Content-Type': 'text/plain; charset=utf-8' } });
}

async function extraRules(): Promise<string[]> {
  try {
    // Строки групп (User-agent) и Sitemap задаёт сам сайт; из админки — только правила
    return (await getSite()).robotsExtra
      .split('\n')
      .map((line) => line.trim())
      .filter((line) => line && !/^(user-agent|sitemap|host):/i.test(line));
  } catch {
    return [];
  }
}
