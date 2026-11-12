/**
 * Клиент API сайта (backend/). На сервере ходит на API_ORIGIN, в браузере — на /api/v1 через прокси Next.
 * Ответы каталога кэшируются в Data Cache Next на 5 минут; теги позволяют сбросить кэш страницы при правке товара.
 */
type Param = string | number | boolean | undefined | null | (string | number)[];

const ORIGIN = typeof window === 'undefined' ? (process.env.API_ORIGIN ?? 'http://127.0.0.1:8001') : '';

export class ApiError extends Error {
  constructor(
    public status: number,
    public code: string,
  ) {
    super(`API ${status} ${code}`);
  }
}

export function apiUrl(path: string, params?: Record<string, Param>): string {
  const search = new URLSearchParams();
  for (const [key, value] of Object.entries(params ?? {})) {
    if (value === undefined || value === null || value === '') continue;
    if (Array.isArray(value)) value.forEach((v) => search.append(key, String(v)));
    else search.set(key, String(value));
  }
  const query = search.toString();
  // В браузере запрос идёт через прокси Next с trailingSlash: слеш на конце избавляет от лишнего редиректа 308
  const tail = ORIGIN === '' && !path.endsWith('/') ? '/' : '';
  return `${ORIGIN}/api/v1${path}${tail}${query ? `?${query}` : ''}`;
}

export interface ApiOptions {
  /** Секунды в Data Cache; false — без кэша */
  revalidate?: number | false;
  tags?: string[];
  method?: 'GET' | 'POST' | 'PUT';
  body?: unknown;
  signal?: AbortSignal;
  /**
   * Адрес посетителя, от имени которого витрина спрашивает API (поиск, подсказки): лимит API считается на этого
   * посетителя (NFR-05), ответ не кэшируется. Без него серверный запрос несёт общий секрет витрины и API и в
   * лимит не входит — его ответ из кэша получают все посетители.
   */
  visitor?: string | null;
}

/**
 * Сколько сервер витрины ждёт ответа API (сбой 12.11.2026: без предела рендер ждал минутами, а API копил очередь
 * из сотен запросов). API под нагрузкой сам отвечает 503 через несколько секунд, так что предел — с запасом.
 */
const SERVER_TIMEOUT_MS = Number(process.env.API_TIMEOUT_MS) || 15_000;

/**
 * Одинаковые запросы разных посетителей, которые идут в API одновременно, — один запрос (сбой 12.11.2026). Кэш Next
 * не помогает, пока он пуст — после выкатки или когда API ошибается: тогда десятки рендеров разом спрашивали шапку,
 * меню и дерево каталога. Только сервер и только общие, кэшируемые GET-запросы.
 */
const inFlight = new Map<string, Promise<unknown>>();

type FetchInit = RequestInit & { next?: { revalidate?: number | false; tags?: string[] } };

async function request<T>(url: string, init: FetchInit): Promise<T> {
  const response = await fetch(url, init);
  if (!response.ok) {
    const data = await response.json().catch(() => ({}));
    throw new ApiError(response.status, typeof data.code === 'string' ? data.code : `HTTP_${response.status}`);
  }
  return (await response.json()) as T;
}

export async function api<T>(path: string, params?: Record<string, Param>, options: ApiOptions = {}): Promise<T> {
  const { tags, method = 'GET', body, signal, visitor } = options;
  const revalidate = visitor ? false : (options.revalidate ?? 300);
  const onServer = typeof window === 'undefined';
  const headers: Record<string, string> = {};
  if (body !== undefined) headers['Content-Type'] = 'application/json';
  if (onServer) {
    if (visitor) headers['X-Forwarded-For'] = visitor;
    else if (process.env.REVALIDATE_SECRET) headers['X-Site-Token'] = process.env.REVALIDATE_SECRET;
  }
  const timeout = onServer ? AbortSignal.timeout(SERVER_TIMEOUT_MS) : undefined;
  const init: FetchInit = {
    method,
    signal: signal && timeout ? AbortSignal.any([signal, timeout]) : (signal ?? timeout),
    headers,
    body: body !== undefined ? JSON.stringify(body) : undefined,
    credentials: 'same-origin',
  };
  const cached = onServer && method === 'GET' && revalidate !== false;
  if (onServer) {
    if (cached) init.next = { revalidate, tags };
    else init.cache = 'no-store';
  }
  // Запрос со своим signal может отменить только его вызывающий — его не делим
  const shared = cached && !signal;
  const url = apiUrl(path, params);
  if (!shared) return request<T>(url, init);
  const key = `${url} ${revalidate} ${tags?.join(',') ?? ''}`;
  const running = inFlight.get(key) as Promise<T> | undefined;
  if (running) return running;
  const started = request<T>(url, init).finally(() => inFlight.delete(key));
  inFlight.set(key, started);
  return started;
}

/** То же, но 404 — это null (страница не найдена) */
export async function apiOrNull<T>(path: string, params?: Record<string, Param>, options?: ApiOptions): Promise<T | null> {
  try {
    return await api<T>(path, params, options);
  } catch (error) {
    if (error instanceof ApiError && error.status === 404) return null;
    throw error;
  }
}

/** Фильтры каталога в параметрах API: f.brand=edqm&f.pack=100-mg; фиксированные фильтры посадочной — p.* */
export function facetParams(prefix: 'f' | 'p', filters?: Partial<Record<string, string[]>>): Record<string, string[]> {
  const out: Record<string, string[]> = {};
  for (const [key, values] of Object.entries(filters ?? {})) if (values?.length) out[`${prefix}.${key}`] = values;
  return out;
}
