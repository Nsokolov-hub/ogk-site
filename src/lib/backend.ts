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
}

export async function api<T>(path: string, params?: Record<string, Param>, options: ApiOptions = {}): Promise<T> {
  const { revalidate = 300, tags, method = 'GET', body, signal } = options;
  const init: RequestInit & { next?: { revalidate?: number | false; tags?: string[] } } = {
    method,
    signal,
    headers: body !== undefined ? { 'Content-Type': 'application/json' } : undefined,
    body: body !== undefined ? JSON.stringify(body) : undefined,
    credentials: 'same-origin',
  };
  if (typeof window === 'undefined') {
    if (method === 'GET' && revalidate !== false) init.next = { revalidate, tags };
    else init.cache = 'no-store';
  }
  const response = await fetch(apiUrl(path, params), init);
  if (!response.ok) {
    const data = await response.json().catch(() => ({}));
    throw new ApiError(response.status, typeof data.code === 'string' ? data.code : `HTTP_${response.status}`);
  }
  return (await response.json()) as T;
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
