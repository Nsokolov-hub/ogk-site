import { NextResponse, type NextRequest } from 'next/server';
import { suggest } from '@/lib/search';

/** GET /api/search/suggest?q=… — подсказки для строки поиска (форма ответа как у будущего /api/v1/public/search/suggest) */
export function GET(request: NextRequest) {
  const q = (request.nextUrl.searchParams.get('q') ?? '').slice(0, 100);
  return NextResponse.json(suggest(q), {
    headers: { 'Cache-Control': 'public, max-age=60' },
  });
}
