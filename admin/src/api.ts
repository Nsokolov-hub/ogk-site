/**
 * Клиент API админки: /api/v1/admin/*. Сессия — httpOnly cookie; каждое изменение несёт CSRF-токен сессии
 * (заголовок X-CSRF-Token), как требует API (ADM-01). 401 — сеанс закончился, приложение показывает вход.
 */

export class ApiError extends Error {
  constructor(
    public status: number,
    public code: string,
    message: string,
    public field?: string | null,
  ) {
    super(message);
  }
}

let csrfToken = '';
export function setCsrf(token: string) {
  csrfToken = token;
}

export const UNAUTHORIZED = 'admin:unauthorized';

type Params = Record<string, string | number | boolean | undefined | null>;

export function query(params?: Params): string {
  const search = new URLSearchParams();
  for (const [key, value] of Object.entries(params ?? {})) {
    if (value === undefined || value === null || value === '') continue;
    search.set(key, String(value));
  }
  const text = search.toString();
  return text ? `?${text}` : '';
}

async function request<T>(method: string, path: string, body?: unknown, form?: FormData): Promise<T> {
  const headers: Record<string, string> = {};
  if (method !== 'GET') headers['X-CSRF-Token'] = csrfToken;
  let payload: BodyInit | undefined;
  if (form) payload = form;
  else if (body !== undefined) {
    headers['Content-Type'] = 'application/json';
    payload = JSON.stringify(body);
  }
  let response: Response;
  try {
    response = await fetch(`/api/v1/admin${path}`, { method, headers, body: payload, credentials: 'same-origin' });
  } catch {
    throw new ApiError(0, 'NETWORK', 'Нет связи с сервером. Проверьте интернет и повторите');
  }
  if (response.status === 401 && !path.startsWith('/auth/login')) window.dispatchEvent(new Event(UNAUTHORIZED));
  if (!response.ok) {
    const data = await response.json().catch(() => ({}));
    throw new ApiError(response.status, data.code ?? `HTTP_${response.status}`, data.message ?? `Ошибка ${response.status}`, data.field);
  }
  return (await response.json()) as T;
}

export const api = {
  get: <T>(path: string, params?: Params) => request<T>('GET', path + query(params)),
  post: <T>(path: string, body?: unknown) => request<T>('POST', path, body ?? {}),
  put: <T>(path: string, body?: unknown) => request<T>('PUT', path, body ?? {}),
  patch: <T>(path: string, body?: unknown) => request<T>('PATCH', path, body ?? {}),
  delete: <T>(path: string) => request<T>('DELETE', path),
  upload: <T>(path: string, file: File) => {
    const form = new FormData();
    form.append('file', file);
    return request<T>('POST', path, undefined, form);
  },
};

/** Адрес для скачивания (CSV, xlsx): браузер идёт по нему с cookie сессии */
export const downloadUrl = (path: string, params?: Params) => `/api/v1/admin${path}${query(params)}`;

export function errorText(error: unknown): string {
  if (error instanceof ApiError) return error.message;
  return error instanceof Error ? error.message : 'Что-то пошло не так';
}
