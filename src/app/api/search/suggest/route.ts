import { NextResponse, type NextRequest } from 'next/server';
import { allLandings, landingFor, landingHref } from '@/lib/landings';
import { suggest } from '@/lib/search';

const startsWord = (text: string, q: string) => {
  const lowered = text.toLowerCase();
  return lowered.startsWith(q) || lowered.split(/[\s,;()[\]/«»"-]+/).some((w) => w.startsWith(q));
};

/**
 * GET /api/search/suggest?q=… — подсказки строки поиска: товары, субстанции, категории и бренды из API сайта
 * плюс SEO-посадочные из админки (ADM-07).
 */
export async function GET(request: NextRequest) {
  const q = (request.nextUrl.searchParams.get('q') ?? '').slice(0, 100);
  const lang = request.nextUrl.searchParams.get('lang') === 'en' ? 'en' : 'ru';
  try {
    const visitor = request.headers.get('x-forwarded-for')?.split(',')[0]?.trim() || null;
    const result = await suggest(q, lang, visitor);
    const query = (result.corrected ?? q).trim().toLowerCase();
    if (query.length >= 3 && result.categories.length < 3) {
      const extra = (await allLandings())
        .map((l) => ({ name: landingFor(l, lang).h1, href: landingHref(l) }))
        .filter((l) => startsWord(l.name, query));
      result.categories = [...result.categories, ...extra].slice(0, 3);
    }
    return NextResponse.json(result, { headers: { 'Cache-Control': 'public, max-age=60' } });
  } catch {
    return NextResponse.json({ code: 'SEARCH_UNAVAILABLE' }, { status: 503, headers: { 'Cache-Control': 'no-store' } });
  }
}
