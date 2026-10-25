import type { Instrumentation } from 'next';

/** Ошибки серверного рендера и маршрутов витрины уходят в Sentry, если задан SENTRY_DSN (lib/error-report) */
export const onRequestError: Instrumentation.onRequestError = async (error, request, context) => {
  const { reportError } = await import('./lib/error-report');
  await reportError(error, { path: request.path, method: request.method, route: context.routePath, kind: context.routeType });
};
