/**
 * Ошибки серверного рендера витрины в Sentry или GlitchTip (ТЗ 12.1) — без SDK: одно событие = один POST
 * в envelope API по SENTRY_DSN. Персональных данных в событии нет: только адрес страницы без параметров и стек.
 */
interface Dsn {
  url: string;
  key: string;
}

function parseDsn(value: string): Dsn | null {
  try {
    const dsn = new URL(value);
    const project = dsn.pathname.replace(/^\/+|\/+$/g, '');
    if (!dsn.username || !project) return null;
    return { url: `${dsn.protocol}//${dsn.host}/api/${project}/envelope/`, key: dsn.username };
  } catch {
    return null;
  }
}

function frames(stack: string | undefined) {
  return (stack ?? '')
    .split('\n')
    .slice(1, 30)
    .map((line) => line.trim().replace(/^at /, ''))
    .filter(Boolean)
    .reverse()
    .map((line) => ({ function: line.slice(0, 200), in_app: !line.includes('node_modules') }));
}

export async function reportError(error: unknown, context: { path?: string; method?: string; route?: string; kind?: string }) {
  const dsn = parseDsn(process.env.SENTRY_DSN ?? '');
  if (!dsn) return;
  const err = error instanceof Error ? error : new Error(String(error));
  const eventId = crypto.randomUUID().replace(/-/g, '');
  const event = {
    event_id: eventId,
    timestamp: Date.now() / 1000,
    platform: 'javascript',
    level: 'error',
    logger: 'storefront',
    server_name: 'web',
    environment: process.env.SITE_ENV || process.env.NODE_ENV,
    exception: { values: [{ type: err.name, value: err.message.slice(0, 1000), stacktrace: { frames: frames(err.stack) } }] },
    request: { url: (context.path ?? '').split('?')[0], method: context.method },
    tags: { route: context.route, kind: context.kind },
  };
  const body = [JSON.stringify({ event_id: eventId, sent_at: new Date().toISOString() }), JSON.stringify({ type: 'event' }), JSON.stringify(event)].join('\n');
  try {
    await fetch(dsn.url, {
      method: 'POST',
      body,
      headers: {
        'Content-Type': 'application/x-sentry-envelope',
        'X-Sentry-Auth': `Sentry sentry_version=7, sentry_client=ogk-storefront/1.0, sentry_key=${dsn.key}`,
      },
      signal: AbortSignal.timeout(3000),
      cache: 'no-store',
    });
  } catch {
    // Сервис ошибок недоступен — ошибка всё равно есть в журнале контейнера
  }
}
