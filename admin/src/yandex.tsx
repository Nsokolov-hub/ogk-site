/**
 * Яндекс Метрика и Вебмастер: подключение токена в настройках и типы отчётов страницы «Аналитика».
 * Токен вставляет администратор; сервер хранит его зашифрованным и отдаёт только последние 4 символа.
 */
import { useState } from 'react';
import { Link } from 'react-router';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { api, errorText } from './api';
import { Badge, Button, Field, formatDate, Panel, TextInput, useToast } from './ui';

interface Access {
  ok: boolean;
  error?: string;
  name?: string;
  login?: string;
  permission?: string;
  host?: string;
}

export interface YandexStatus {
  connected: boolean;
  source: 'admin' | 'server' | null;
  tail: string | null;
  login: string | null;
  savedAt: string | null;
  savedBy: string | null;
  access: { metrika?: Access; webmaster?: Access };
  counter: string | null;
  refreshedAt: string | null;
  tokenInvalid: boolean;
}

export interface Goal {
  id: number;
  name: string;
  identifier: string | null;
  reaches: number;
  conversion: number;
}

export interface MetrikaReport {
  counter: string | null;
  errors: string[];
  missingGoals: string[];
  totals?: { visits: number; users: number; pageviews: number; bounceRate: number; duration: number };
  days?: { date: string; visits: number; users: number }[];
  sources?: { key: string | null; name: string; visits: number; users: number }[];
  engines?: { name: string; visits: number }[];
  pages?: { path: string; visits: number; bounceRate: number }[];
  goals?: Goal[];
}

export interface WebmasterReport {
  host: string | null;
  errors: string[];
  summary?: { inSearch: number; excluded: number; sqi: number; problems: Record<string, number> };
  problems?: { code: string; title: string; severity: string; severityTitle: string }[];
  sitemaps?: { url: string; urls: number; errors: number; children: number; lastAccess: string | null; added: boolean }[];
  removed?: { title: string; count: number; examples: string[] }[];
  queries?: { text: string; shows: number; clicks: number; position: number }[];
  queryTotals?: { shows: number; clicks: number; days: { date: string; shows: number; clicks: number }[] };
  inSearch?: { date: string; value: number | null }[];
  crawled?: { ok: number; redirect: number; notFound: number; error: number };
}

export interface AnalyticsData {
  status: YandexStatus;
  period: number;
  fetchedAt: string | null;
  metrika: MetrikaReport | null;
  webmaster: WebmasterReport | null;
}

interface GoalResult {
  identifier: string;
  name: string;
  state: 'exists' | 'created' | 'error';
  error?: string;
}

interface ConnectResult {
  status: YandexStatus;
  access: { metrika: Access; webmaster: Access };
  goals: GoalResult[] | string;
}

export const analyticsQuery = (period: number) => ({
  queryKey: ['analytics', period],
  queryFn: () => api.get<AnalyticsData>('/analytics', { period }),
});

function AccessLine({ label, access }: { label: string; access?: Access }) {
  if (!access) return null;
  return (
    <li>
      {label}: {access.ok ? <Badge tone="good">есть доступ</Badge> : <Badge tone="bad">нет доступа</Badge>}{' '}
      <span className="muted">{access.ok ? access.name || access.host || '' : access.error}</span>
    </li>
  );
}

export function goalsSummary(goals: GoalResult[] | string): string {
  if (typeof goals === 'string') return `Цели не созданы: ${goals}`;
  const created = goals.filter((g) => g.state === 'created').length;
  const failed = goals.filter((g) => g.state === 'error');
  const parts = [`создано целей: ${created}`, `уже были: ${goals.length - created - failed.length}`];
  if (failed.length) parts.push(`не удалось: ${failed.length} (${failed[0].error})`);
  return `Цели Метрики — ${parts.join(', ')}`;
}

/** Блок настроек: подключён ли Яндекс, поле для токена, инструкция */
export function YandexPanel({ admin }: { admin: boolean }) {
  const toast = useToast();
  const client = useQueryClient();
  const data = useQuery(analyticsQuery(30));
  const [token, setToken] = useState('');
  const [result, setResult] = useState<ConnectResult | null>(null);
  const connect = useMutation({
    mutationFn: () => api.put<ConnectResult>('/analytics/token', { token }),
    onSuccess: (r) => {
      setToken('');
      setResult(r);
      toast('Яндекс подключён — отчёты появятся в «Аналитике» в течение минуты');
      void client.invalidateQueries({ queryKey: ['analytics'] });
    },
    onError: (e) => toast(errorText(e), 'bad'),
  });
  const disconnect = useMutation({
    mutationFn: () => api.delete<{ status: YandexStatus }>('/analytics/token'),
    onSuccess: () => {
      setResult(null);
      toast('Яндекс отключён');
      void client.invalidateQueries({ queryKey: ['analytics'] });
    },
    onError: (e) => toast(errorText(e), 'bad'),
  });
  const status = data.data?.status;
  const access = result?.access ?? status?.access;

  return (
    <Panel title="Яндекс Метрика и Вебмастер" actions={status?.connected ? <Link to="/analytics">Открыть аналитику →</Link> : null}>
      <div className="stack">
        {status ? (
          <div>
            <p style={{ margin: 0 }}>
              {status.tokenInvalid ? (
                <Badge tone="bad">токен не работает — вставьте новый</Badge>
              ) : status.connected ? (
                <Badge tone="good">подключён</Badge>
              ) : (
                <Badge tone="warn">не подключён</Badge>
              )}{' '}
              {status.source === 'admin' ? (
                <span className="muted small">
                  {status.login ? `аккаунт ${status.login} · ` : ''}токен …{status.tail} · сохранил {status.savedBy}, {formatDate(status.savedAt)}
                </span>
              ) : status.source === 'server' ? (
                <span className="muted small">токен из настроек сервера (METRIKA_OAUTH_TOKEN)</span>
              ) : null}
            </p>
            {access && (access.metrika || access.webmaster) ? (
              <ul className="small" style={{ margin: '8px 0 0', paddingLeft: 18 }}>
                <AccessLine label="Метрика" access={access.metrika} />
                <AccessLine label="Вебмастер" access={access.webmaster} />
              </ul>
            ) : null}
            {result ? <p className="small" style={{ margin: '8px 0 0' }}>{goalsSummary(result.goals)}</p> : null}
          </div>
        ) : null}
        {admin ? (
          <>
            <Field label={status?.connected ? 'Новый токен (заменит текущий)' : 'Токен Яндекса'} hint="Длинная строка, начинается на y0_. Хранится на сервере в зашифрованном виде; здесь видны только последние 4 символа">
              <TextInput type="password" autoComplete="off" spellCheck={false} placeholder="y0_…" value={token} onChange={(e) => setToken(e.target.value)} />
            </Field>
            <div className="row">
              <Button size="sm" variant="primary" busy={connect.isPending} disabled={!token.trim()} onClick={() => connect.mutate()}>
                {status?.connected ? 'Заменить токен' : 'Подключить'}
              </Button>
              {status?.source === 'admin' ? (
                <Button size="sm" variant="ghost" busy={disconnect.isPending} onClick={() => window.confirm('Отключить Яндекс? Отчёты и выгрузка конверсий из CRM остановятся') && disconnect.mutate()}>
                  Отключить
                </Button>
              ) : null}
            </div>
            <details className="small">
              <summary>Как получить токен</summary>
              <ol style={{ paddingLeft: 18 }}>
                <li>Войдите в Яндекс под аккаунтом, которому принадлежат счётчик Метрики и сайт в Вебмастере.</li>
                <li>
                  Откройте <a href="https://oauth.yandex.ru/client/new" target="_blank" rel="noreferrer">oauth.yandex.ru/client/new</a>, выберите доступ к API и отметьте права{' '}
                  <code>metrika:read</code>, <code>metrika:write</code>, <code>webmaster:hostinfo</code>, <code>webmaster:verify</code>.
                </li>
                <li>
                  После создания откройте <code>https://oauth.yandex.ru/authorize?response_type=token&amp;client_id=ClientID</code>, подставив ClientID приложения, и нажмите «Разрешить».
                </li>
                <li>Скопируйте токен со страницы Яндекса и вставьте сюда. Токен действует около года.</li>
              </ol>
            </details>
          </>
        ) : null}
        <p className="muted small" style={{ margin: 0 }}>
          Токен нужен для отчётов в «Аналитике», целей Метрики и выгрузки результатов заявок из CRM (квалифицирована, КП, продажа) в Метрику.
        </p>
      </div>
    </Panel>
  );
}
