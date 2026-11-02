/** Аналитика: посещаемость и цели из Яндекс Метрики, поиск и индексация из Вебмастера. Данные обновляются раз в час. */
import { useState } from 'react';
import { Link } from 'react-router';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { api, errorText } from '../api';
import { useAuth } from '../auth';
import { analyticsQuery, goalsSummary, type AnalyticsData, type MetrikaReport, type WebmasterReport } from '../yandex';
import { Badge, Button, Empty, ErrorBox, formatDate, Loading, PageHeader, Panel, Tabs, useToast } from '../ui';

type Period = '7' | '30' | '90';

const n = (value: number | undefined | null) => (value ?? 0).toLocaleString('ru-RU');
const pct = (part: number, whole: number) => (whole ? `${((part / whole) * 100).toLocaleString('ru-RU', { maximumFractionDigits: 1 })}%` : '—');
const day = (iso: string) => `${iso.slice(8, 10)}.${iso.slice(5, 7)}`;
const duration = (seconds: number) => `${Math.floor(seconds / 60)}:${String(seconds % 60).padStart(2, '0')}`;
const SITE = 'https://www.ogk-chem.ru';

/** Линия по дням; пропуски (null) — разрыв линии. Подсказка с числом — при наведении на день. */
function LineChart({ points, label }: { points: { date: string; value: number | null }[]; label: string }) {
  const W = 640;
  const H = 150;
  const values = points.map((p) => p.value).filter((v): v is number => v !== null);
  if (!values.length || values.every((v) => v === 0)) return <p className="muted small">За период данных пока нет</p>;
  const max = Math.max(...values);
  const x = (i: number) => (points.length === 1 ? W / 2 : (i * W) / (points.length - 1));
  const y = (v: number) => H - 2 - (v / max) * (H - 12);
  const segments: string[][] = [];
  let current: string[] = [];
  points.forEach((p, i) => {
    if (p.value === null) {
      if (current.length) segments.push(current);
      current = [];
      return;
    }
    current.push(`${x(i).toFixed(1)},${y(p.value).toFixed(1)}`);
  });
  if (current.length) segments.push(current);
  const step = W / Math.max(points.length, 1);
  return (
    <figure className="chart">
      <svg viewBox={`0 0 ${W} ${H}`} preserveAspectRatio="none" role="img" aria-label={label}>
        <line x1={0} x2={W} y1={y(max)} y2={y(max)} className="chart-grid" />
        <line x1={0} x2={W} y1={H - 2} y2={H - 2} className="chart-grid" />
        {segments.map((s) => (
          <g key={s[0]}>
            <polygon points={`${s[0].split(',')[0]},${H - 2} ${s.join(' ')} ${s[s.length - 1].split(',')[0]},${H - 2}`} className="chart-area" />
            <polyline points={s.join(' ')} className="chart-line" />
          </g>
        ))}
        {points.map((p, i) => (
          <rect key={p.date} x={x(i) - step / 2} y={0} width={step} height={H} fill="transparent">
            <title>{`${day(p.date)}: ${p.value === null ? 'нет данных' : n(p.value)}`}</title>
          </rect>
        ))}
      </svg>
      <figcaption className="chart-axis">
        <span>{day(points[0].date)}</span>
        <span>
          {label}, максимум {n(max)}
        </span>
        <span>{day(points[points.length - 1].date)}</span>
      </figcaption>
    </figure>
  );
}

function Errors({ errors }: { errors: string[] }) {
  if (!errors.length) return null;
  return (
    <div className="warn-box small">
      {errors.map((e) => (
        <div key={e}>{e}</div>
      ))}
    </div>
  );
}

function Metrika({ m, admin, period }: { m: MetrikaReport; admin: boolean; period: number }) {
  const toast = useToast();
  const client = useQueryClient();
  const goals = useMutation({
    mutationFn: () => api.post<{ goals: Parameters<typeof goalsSummary>[0] }>('/analytics/goals'),
    onSuccess: (r) => {
      toast(goalsSummary(r.goals));
      void client.invalidateQueries({ queryKey: ['analytics'] });
    },
    onError: (e) => toast(errorText(e), 'bad'),
  });
  const t = m.totals;
  const sourceTotal = (m.sources ?? []).reduce((a, s) => a + s.visits, 0);
  const goalsSorted = [...(m.goals ?? [])].sort((a, b) => b.reaches - a.reaches);
  return (
    <Panel
      title="Посещаемость — Яндекс Метрика"
      actions={m.counter ? <a href={`https://metrika.yandex.ru/dashboard?id=${m.counter}&period=${period === 7 ? 'week' : period === 30 ? 'month' : 'quarter'}`} target="_blank" rel="noreferrer">Открыть Метрику ↗</a> : null}
    >
      <Errors errors={m.errors} />
      {t ? (
        <div className="grid-5">
          <div className="stat"><strong>{n(t.visits)}</strong><span>визитов</span></div>
          <div className="stat"><strong>{n(t.users)}</strong><span>посетителей</span></div>
          <div className="stat"><strong>{n(t.pageviews)}</strong><span>просмотров страниц</span></div>
          <div className="stat"><strong>{t.bounceRate.toLocaleString('ru-RU')}%</strong><span>отказов</span></div>
          <div className="stat"><strong>{duration(t.duration)}</strong><span>среднее время на сайте</span></div>
        </div>
      ) : null}
      {m.days ? <LineChart label="Визиты по дням" points={m.days.map((d) => ({ date: d.date, value: d.visits }))} /> : null}

      <div className="grid-2" style={{ marginTop: 16 }}>
        <div>
          <h3>Откуда приходят</h3>
          <table className="table">
            <tbody>
              {(m.sources ?? []).map((s) => (
                <tr key={s.name}>
                  <td>{s.name}</td>
                  <td className="num">{n(s.visits)}</td>
                  <td className="num muted">{pct(s.visits, sourceTotal)}</td>
                </tr>
              ))}
              {!m.sources?.length ? <tr><td className="muted">Визитов пока нет</td></tr> : null}
            </tbody>
          </table>
          {m.engines?.length ? (
            <>
              <h3 style={{ marginTop: 16 }}>Из поисковиков</h3>
              <table className="table">
                <tbody>
                  {m.engines.map((e) => (
                    <tr key={e.name}>
                      <td>{e.name}</td>
                      <td className="num">{n(e.visits)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </>
          ) : null}
        </div>
        <div>
          <h3>Страницы входа</h3>
          <table className="table">
            <thead>
              <tr><th>Страница</th><th className="num">Визиты</th><th className="num">Отказы</th></tr>
            </thead>
            <tbody>
              {(m.pages ?? []).map((p) => (
                <tr key={p.path}>
                  <td style={{ wordBreak: 'break-all' }}>
                    <a href={`${SITE}${p.path}`} target="_blank" rel="noreferrer">{p.path}</a>
                  </td>
                  <td className="num">{n(p.visits)}</td>
                  <td className="num muted">{p.bounceRate.toLocaleString('ru-RU')}%</td>
                </tr>
              ))}
              {!m.pages?.length ? <tr><td colSpan={3} className="muted">Визитов пока нет</td></tr> : null}
            </tbody>
          </table>
        </div>
      </div>

      <h3 style={{ marginTop: 16 }}>Цели</h3>
      {m.missingGoals.length ? (
        <div className="warn-box small row">
          <span className="grow">В Метрике нет целей для событий сайта: {m.missingGoals.join(', ')}. Без них заявки и клики не видны в отчётах.</span>
          {admin ? <Button size="sm" busy={goals.isPending} onClick={() => goals.mutate()}>Создать цели</Button> : null}
        </div>
      ) : null}
      <div className="table-wrap">
        <table className="table">
          <thead>
            <tr><th>Цель</th><th className="num">Достижений</th><th className="num">Конверсия</th></tr>
          </thead>
          <tbody>
            {goalsSorted.map((g) => (
              <tr key={g.id}>
                <td>
                  {g.name} {g.identifier ? <code>{g.identifier}</code> : null}
                </td>
                <td className="num">{n(g.reaches)}</td>
                <td className="num muted">{g.conversion.toLocaleString('ru-RU')}%</td>
              </tr>
            ))}
            {!goalsSorted.length ? <tr><td colSpan={3} className="muted">Целей нет</td></tr> : null}
          </tbody>
        </table>
      </div>
      <p className="muted small">Цели «CRM: …» Метрика получает из CRM, когда заявка с сайта взята в работу, по ней отправлено КП или прошла продажа.</p>
    </Panel>
  );
}

function Webmaster({ w, admin }: { w: WebmasterReport; admin: boolean }) {
  const toast = useToast();
  const client = useQueryClient();
  const sitemap = useMutation({
    mutationFn: () => api.post<{ url: string; state: string }>('/analytics/sitemap'),
    onSuccess: (r) => {
      toast(r.state === 'added' ? `Sitemap добавлен в Вебмастер: ${r.url}` : 'Sitemap уже был добавлен');
      void client.invalidateQueries({ queryKey: ['analytics'] });
    },
    onError: (e) => toast(errorText(e), 'bad'),
  });
  const s = w.summary;
  const q = w.queryTotals;
  const hasOwnSitemap = (w.sitemaps ?? []).some((x) => x.added && x.url.endsWith('/sitemap.xml'));
  return (
    <Panel title="Поиск — Яндекс Вебмастер" actions={<a href="https://webmaster.yandex.ru/sites/" target="_blank" rel="noreferrer">Открыть Вебмастер ↗</a>}>
      <Errors errors={w.errors} />
      <div className="grid-5">
        {s ? (
          <>
            <div className="stat"><strong>{n(s.inSearch)}</strong><span>страниц в поиске</span></div>
            <div className="stat"><strong>{n(s.excluded)}</strong><span>исключено из поиска</span></div>
            <div className="stat"><strong>{n(s.sqi)}</strong><span>ИКС сайта</span></div>
          </>
        ) : null}
        {q ? (
          <>
            <div className="stat"><strong>{n(q.shows)}</strong><span>показов в поиске за период</span></div>
            <div className="stat"><strong>{n(q.clicks)}</strong><span>кликов, CTR {pct(q.clicks, q.shows)}</span></div>
          </>
        ) : null}
      </div>
      <p className="muted small">Вебмастер считает показы и клики с задержкой в несколько дней; число страниц в поиске обновляется раз в несколько дней.</p>
      <div className="grid-2">
        {w.inSearch ? <LineChart label="Страниц в поиске" points={w.inSearch} /> : null}
        {q ? <LineChart label="Показы по дням" points={q.days.map((d) => ({ date: d.date, value: d.shows }))} /> : null}
      </div>

      <h3 style={{ marginTop: 16 }}>Поисковые запросы</h3>
      <div className="table-wrap">
        <table className="table">
          <thead>
            <tr><th>Запрос</th><th className="num">Показы</th><th className="num">Клики</th><th className="num">CTR</th><th className="num">Позиция</th></tr>
          </thead>
          <tbody>
            {(w.queries ?? []).map((r) => (
              <tr key={r.text}>
                <td>{r.text}</td>
                <td className="num">{n(r.shows)}</td>
                <td className="num">{n(r.clicks)}</td>
                <td className="num muted">{pct(r.clicks, r.shows)}</td>
                <td className="num">{r.position.toLocaleString('ru-RU')}</td>
              </tr>
            ))}
            {!w.queries?.length ? <tr><td colSpan={5} className="muted">Запросов за период пока нет</td></tr> : null}
          </tbody>
        </table>
      </div>

      <div className="grid-2" style={{ marginTop: 16 }}>
        <div>
          <h3>Почему страницы выпадают из поиска</h3>
          {w.removed?.length ? (
            <table className="table">
              <tbody>
                {w.removed.map((r) => (
                  <tr key={r.title}>
                    <td>
                      {r.title}
                      <div className="muted small" style={{ wordBreak: 'break-all' }}>{r.examples.slice(0, 2).join(', ')}</div>
                    </td>
                    <td className="num">{n(r.count)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            <p className="muted small">Недавно из поиска ничего не выпадало</p>
          )}
          <p className="muted small">По последним 100 событиям Вебмастера.</p>
        </div>
        <div>
          <h3>Проблемы сайта</h3>
          {w.problems?.length ? (
            <table className="table">
              <tbody>
                {w.problems.map((p) => (
                  <tr key={p.code}>
                    <td>{p.title}</td>
                    <td className="num">
                      <Badge tone={p.severity === 'FATAL' || p.severity === 'CRITICAL' ? 'bad' : p.severity === 'POSSIBLE_PROBLEM' ? 'warn' : 'info'}>{p.severityTitle}</Badge>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            <p className="muted small">Вебмастер проблем не нашёл</p>
          )}
          {w.crawled ? (
            <>
              <h3 style={{ marginTop: 16 }}>Робот обошёл за период</h3>
              <p className="small" style={{ margin: '6px 0 0' }}>
                {n(w.crawled.ok)} страниц с ответом 200 · {n(w.crawled.redirect)} перенаправлений · {n(w.crawled.notFound)} не найдено (4xx) · {n(w.crawled.error)} ошибок
              </p>
            </>
          ) : null}
        </div>
      </div>

      <h3 style={{ marginTop: 16 }}>Файлы Sitemap</h3>
      <div className="table-wrap">
        <table className="table">
          <thead>
            <tr><th>Файл</th><th className="num">Адресов</th><th className="num">Вложенных</th><th className="num">Ошибок</th><th>Робот загружал</th></tr>
          </thead>
          <tbody>
            {(w.sitemaps ?? []).map((x) => (
              <tr key={x.url}>
                <td style={{ wordBreak: 'break-all' }}>
                  {x.url} {x.added ? <Badge tone="info">добавлен вручную</Badge> : null}
                </td>
                <td className="num">{n(x.urls)}</td>
                <td className="num">{n(x.children)}</td>
                <td className="num">{x.errors ? <Badge tone="bad">{n(x.errors)}</Badge> : '0'}</td>
                <td className="nowrap">{formatDate(x.lastAccess)}</td>
              </tr>
            ))}
            {!w.sitemaps?.length ? <tr><td colSpan={5} className="muted">Вебмастер ещё не нашёл Sitemap</td></tr> : null}
          </tbody>
        </table>
      </div>
      {admin && !hasOwnSitemap && w.host ? (
        <div className="row" style={{ marginTop: 10 }}>
          <Button size="sm" busy={sitemap.isPending} onClick={() => sitemap.mutate()}>Добавить sitemap.xml в Вебмастер</Button>
          <span className="muted small">Яндекс и так находит его через robots.txt; добавление ускоряет первую загрузку.</span>
        </div>
      ) : null}
    </Panel>
  );
}

export function Analytics() {
  const { can } = useAuth();
  const admin = can('settings.write');
  const toast = useToast();
  const client = useQueryClient();
  const [period, setPeriod] = useState<Period>('30');
  const data = useQuery({
    ...analyticsQuery(Number(period)),
    // Сразу после подключения отчётов ещё нет: worker загрузит их в течение минуты.
    refetchInterval: (q) => (q.state.data?.status.connected && !q.state.data.fetchedAt ? 20_000 : false),
  });
  const refresh = useMutation({
    mutationFn: () => api.post<AnalyticsData>(`/analytics/refresh?period=${period}`),
    onSuccess: (r) => {
      client.setQueryData(['analytics', Number(period)], r);
      void client.invalidateQueries({ queryKey: ['analytics'] });
      toast('Данные обновлены');
    },
    onError: (e) => toast(errorText(e), 'bad'),
  });
  if (data.isLoading) return <Loading />;
  if (data.error || !data.data) return <ErrorBox error={data.error} retry={() => void data.refetch()} />;
  const d = data.data;
  const header = (
    <PageHeader
      title="Аналитика"
      description={d.fetchedAt ? `Яндекс Метрика и Вебмастер · данные на ${formatDate(d.fetchedAt)}, обновляются раз в час` : 'Яндекс Метрика и Вебмастер'}
      actions={admin && d.status.connected ? <Button size="sm" busy={refresh.isPending} onClick={() => refresh.mutate()}>Обновить сейчас</Button> : null}
    />
  );
  if (!d.status.connected) {
    return (
      <>
        {header}
        <Panel>
          <Empty title="Яндекс не подключён">
            {admin ? (
              <>
                Вставьте токен Яндекса в <Link to="/settings">Настройках</Link> — блок «Яндекс Метрика и Вебмастер».
              </>
            ) : (
              'Подключить может администратор в Настройках.'
            )}
          </Empty>
        </Panel>
      </>
    );
  }
  return (
    <>
      {header}
      {d.status.tokenInvalid ? (
        <div className="error-box">
          <span>Яндекс не принимает токен: он отозван или истёк. {admin ? <Link to="/settings">Вставьте новый в Настройках</Link> : 'Сообщите администратору.'}</span>
        </div>
      ) : null}
      <Tabs value={period} onChange={setPeriod} items={[{ key: '7', label: '7 дней' }, { key: '30', label: '30 дней' }, { key: '90', label: '90 дней' }]} />
      {!d.fetchedAt ? <Loading text="Загружаем отчёты из Яндекса — обычно это меньше минуты…" /> : null}
      {d.metrika ? <Metrika m={d.metrika} admin={admin} period={Number(period)} /> : null}
      {d.webmaster ? <Webmaster w={d.webmaster} admin={admin} /> : null}
    </>
  );
}
