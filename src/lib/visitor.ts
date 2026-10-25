import { headers } from 'next/headers';

/** Адрес посетителя из X-Forwarded-For, который ставит Caddy (в разработке его нет — тогда null) */
export async function visitorAddress(): Promise<string | null> {
  try {
    const value = (await headers()).get('x-forwarded-for');
    return value?.split(',')[0]?.trim() || null;
  } catch {
    return null;
  }
}
