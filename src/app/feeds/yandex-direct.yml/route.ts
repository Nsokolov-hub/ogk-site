import { yandexDirectYml } from '@/lib/feed';

/** /feeds/yandex-direct.yml — товарный фид Директа (ТЗ 15.4), обновляется каждые 6 часов */
export const dynamic = 'force-dynamic';

export async function GET() {
  return new Response(await yandexDirectYml(), {
    headers: { 'Content-Type': 'application/xml; charset=utf-8', 'Cache-Control': 'public, max-age=21600' },
  });
}
