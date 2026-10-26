import { Link } from 'react-router';
import { useQuery } from '@tanstack/react-query';
import { api } from '../api';
import { Badge, ErrorBox, formatDate, Loading, PageHeader, Panel } from '../ui';

interface DashboardData {
  products: { byStatus: Record<string, number>; total: number; indexable: number };
  queues: Record<string, number>;
  requests: { week: number; undelivered: number; failed: number };
  content: { pages: number; drafts: number; scheduled: number };
  lastImport: { fileName: string; status: string; startedAt: string; counters: Record<string, number> } | null;
  integration: { crmUrl: string; deliveryEnabled: boolean; lastDeliveredAt: string | null; pending: number; brandsSyncedAt: string | null };
}

const n = (value: number | undefined) => (value ?? 0).toLocaleString('ru-RU');

export function Dashboard() {
  const data = useQuery({ queryKey: ['dashboard'], queryFn: () => api.get<DashboardData>('/dashboard'), refetchInterval: 60_000 });
  if (data.isLoading) return <Loading />;
  if (data.error || !data.data) return <ErrorBox error={data.error} retry={() => void data.refetch()} />;
  const d = data.data;
  const q = d.queues;
  return (
    <>
      <PageHeader title="Сводка" description="Каталог, очереди, заявки и связь с CRM. Обновляется раз в минуту." />
      <div className="grid-3">
        <Link className="stat" to="/products">
          <strong>{n(d.products.total)}</strong>
          <span>товаров, из них опубликовано {n(d.products.byStatus.published)}</span>
        </Link>
        <Link className="stat" to="/products?indexable=true">
          <strong>{n(d.products.indexable)}</strong>
          <span>карточек индексируется поисковиками (SEO-07)</span>
        </Link>
        <Link className="stat" to="/requests">
          <strong>{n(d.requests.week)}</strong>
          <span>заявок за 7 дней</span>
        </Link>
        <Link className="stat" to="/requests?status=failed">
          <strong style={{ color: d.requests.failed ? 'var(--danger)' : undefined }}>{n(d.requests.undelivered)}</strong>
          <span>не доставлено в CRM, из них ошибок {n(d.requests.failed)}</span>
        </Link>
        <Link className="stat" to="/pages">
          <strong>{n(d.content.drafts)}</strong>
          <span>черновиков, запланировано {n(d.content.scheduled)}</span>
        </Link>
      </div>
      <div className="grid-2" style={{ marginTop: 16 }}>
        <Panel title="Очереди">
          <table className="table">
            <tbody>
              {[
                ['Конфликты CAS', q.conflicts, '/queues?tab=conflicts'],
                ['Новые производители из импорта', q.brands, '/queues?tab=brands'],
                ['Спорные подконтрольные', q.controlled, '/queues?tab=controlled'],
                ['На модерации', q.moderation, '/products?status=moderation'],
                ['Без раздела каталога', q.noCategory, '/products?no_category=true'],
                ['Запросы без результатов за 30 дней', q.misses, '/queues?tab=misses'],
              ].map(([label, count, to]) => (
                <tr key={String(label)}>
                  <td>
                    <Link to={String(to)}>{label}</Link>
                  </td>
                  <td className="num">{count ? <Badge tone="warn">{n(Number(count))}</Badge> : <span className="muted">0</span>}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </Panel>
        <Panel title="Связь с CRM">
          <p>
            Доставка заявок:{' '}
            {d.integration.deliveryEnabled ? <Badge tone="good">включена</Badge> : <Badge tone="warn">выключена — заявки ждут в очереди и уходят на почту</Badge>}
          </p>
          <p className="muted">
            Последняя заявка доставлена: {formatDate(d.integration.lastDeliveredAt)} · в очереди: {d.integration.pending}
          </p>
          <p className="muted">Реестр производителей из CRM: {formatDate(d.integration.brandsSyncedAt)}</p>
          {d.lastImport ? (
            <p className="muted">
              Последний импорт: {d.lastImport.fileName} — {d.lastImport.status}, {formatDate(d.lastImport.startedAt)}
            </p>
          ) : null}
        </Panel>
      </div>
    </>
  );
}
