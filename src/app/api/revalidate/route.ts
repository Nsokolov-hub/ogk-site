import { revalidateTag } from 'next/cache';
import { NextResponse, type NextRequest } from 'next/server';

/**
 * POST /api/revalidate/ {tags: ['product:slug', 'catalog']} — воркер API сбрасывает кэш данных изменённых страниц.
 * Заголовок X-Revalidate-Secret = REVALIDATE_SECRET; без секрета маршрут выключен.
 */
export async function POST(request: NextRequest) {
  const secret = process.env.REVALIDATE_SECRET;
  if (!secret || request.headers.get('x-revalidate-secret') !== secret) {
    return NextResponse.json({ code: 'FORBIDDEN' }, { status: 403 });
  }
  const body = (await request.json().catch(() => ({}))) as { tags?: unknown };
  const tags = Array.isArray(body.tags) ? body.tags.filter((t): t is string => typeof t === 'string' && t.length <= 300).slice(0, 2000) : [];
  for (const tag of tags) revalidateTag(tag);
  return NextResponse.json({ revalidated: tags.length }, { headers: { 'Cache-Control': 'no-store' } });
}
