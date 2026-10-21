import { NextResponse, type NextRequest } from 'next/server';
import { BATCH_LIMIT, matchLines } from '@/lib/search';

/**
 * POST /api/search/batch {lines: string[]} — сопоставление списка с каталогом (SRCH-09).
 * В проде — /api/v1/public/search/batch с лимитом запросов (NFR-05).
 */
export async function POST(request: NextRequest) {
  let lines: unknown;
  try {
    ({ lines } = (await request.json()) as { lines?: unknown });
  } catch {
    return NextResponse.json({ error: 'bad_request' }, { status: 400 });
  }
  if (!Array.isArray(lines)) return NextResponse.json({ error: 'bad_request' }, { status: 400 });
  const clean = lines
    .filter((l): l is string => typeof l === 'string')
    .slice(0, BATCH_LIMIT)
    .map((l) => l.slice(0, 200));
  return NextResponse.json({ results: matchLines(clean) }, { headers: { 'Cache-Control': 'no-store' } });
}
