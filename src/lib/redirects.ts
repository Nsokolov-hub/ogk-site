/**
 * Редиректы из админки (ADM-07, URL-03, URL-11) в middleware витрины: карта адресов берётся из API раз в минуту
 * и живёт в памяти процесса. API недоступен — работает прежняя карта, сайт не ждёт.
 */
interface Rule {
  target: string;
  code: 301 | 302;
}

const TTL_MS = 60_000;
let cache: { at: number; rules: Map<string, Rule> } = { at: 0, rules: new Map() };
let loading: Promise<void> | null = null;

async function load(): Promise<void> {
  const origin = process.env.API_ORIGIN ?? 'http://127.0.0.1:8001';
  try {
    const headers: Record<string, string> = {};
    if (process.env.REVALIDATE_SECRET) headers['X-Site-Token'] = process.env.REVALIDATE_SECRET;
    const response = await fetch(`${origin}/api/v1/public/redirects`, { headers, cache: 'no-store', signal: AbortSignal.timeout(1500) });
    if (!response.ok) throw new Error(String(response.status));
    const rows = (await response.json()) as { source: string; target: string; code: number }[];
    cache = { at: Date.now(), rules: new Map(rows.map((r) => [r.source, { target: r.target, code: r.code === 302 ? 302 : 301 }])) };
  } catch {
    cache = { ...cache, at: Date.now() };
  }
}

/** Правило для пути; /en/-адрес ищется без префикса и ведёт на /en/-версию цели */
export async function findRedirect(pathname: string): Promise<Rule | null> {
  if (Date.now() - cache.at > TTL_MS) {
    loading ??= load().finally(() => {
      loading = null;
    });
    await loading;
  }
  const direct = cache.rules.get(pathname);
  if (direct) return direct;
  if (pathname.startsWith('/en/')) {
    const rule = cache.rules.get(pathname.slice(3));
    if (rule) return { ...rule, target: rule.target.startsWith('/') ? `/en${rule.target}` : rule.target };
  }
  return null;
}
