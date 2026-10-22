import { yandexDirectYml } from '@/lib/feed';

/** /feeds/yandex-direct.yml — товарный фид Директа (ТЗ 15.4), обновляется каждые 6 часов */
export const revalidate = 21600;

export function GET() {
  return new Response(yandexDirectYml(), { headers: { 'Content-Type': 'application/xml; charset=utf-8' } });
}
