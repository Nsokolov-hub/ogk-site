/** Очереди каталог-менеджера (ADM-05): конфликты CAS, новые производители, подконтрольные, «обогатить», спрос без товара. */
import { useState } from 'react';
import { Link, useSearchParams } from 'react-router';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { api, errorText } from '../api';
import { useAuth } from '../auth';
import { Badge, Button, Empty, ErrorBox, formatDate, Loading, PageHeader, Pagination, Panel, Select, Tabs, useDebounced, useToast } from '../ui';

type Tab = 'conflicts' | 'brands' | 'controlled' | 'enrich' | 'misses';

export function Queues() {
  const [params, setParams] = useSearchParams();
  const tab = (params.get('tab') as Tab) || 'conflicts';
  const counts = useQuery({ queryKey: ['queues'], queryFn: () => api.get<Record<string, number>>('/queues') });
  const c = counts.data ?? {};
  return (
    <>
      <PageHeader
        title="Очереди"
        description={
          <>
            Что требует решения человека. Товары на модерации и без раздела — в <Link to="/products?status=moderation">списке товаров</Link> с фильтром.
          </>
        }
      />
      <Tabs
        value={tab}
        onChange={(t) => setParams({ tab: t })}
        items={[
          { key: 'conflicts', label: `Конфликты CAS · ${c.conflicts ?? 0}` },
          { key: 'brands', label: `Новые производители · ${c.brands ?? 0}` },
          { key: 'controlled', label: `Подконтрольные · ${c.controlled ?? 0}` },
          { key: 'enrich', label: 'Обогатить по спросу' },
          { key: 'misses', label: `Спрос без товара · ${c.misses ?? 0}` },
        ]}
      />
      {tab === 'conflicts' ? <Conflicts /> : null}
      {tab === 'brands' ? <NewBrands /> : null}
      {tab === 'controlled' ? <Controlled /> : null}
      {tab === 'enrich' ? <Enrich /> : null}
      {tab === 'misses' ? <Misses /> : null}
    </>
  );
}

function useAct<T>(path: (arg: T) => string, body: (arg: T) => unknown, done: string) {
  const toast = useToast();
  const client = useQueryClient();
  return useMutation({
    mutationFn: (arg: T) => api.post(path(arg), body(arg)),
    onSuccess: () => {
      toast(done);
      void client.invalidateQueries({ queryKey: ['queues'] });
      void client.invalidateQueries({ queryKey: ['queue'] });
    },
    onError: (e) => toast(errorText(e), 'bad'),
  });
}

function Conflicts() {
  const { can } = useAuth();
  const [page, setPage] = useState(1);
  const list = useQuery({ queryKey: ['queue', 'conflicts', page], queryFn: () => api.get<{ total: number; items: { id: number; message: string; values: Record<string, string>; productId: string | null; product: string | null; currentCas: string | null }[] }>('/queues/conflicts', { page }) });
  const act = useAct<{ id: number; action: string }>((a) => `/queues/conflicts/${a.id}`, (a) => ({ action: a.action }), 'Конфликт решён');
  if (list.isLoading) return <Loading />;
  return (
    <Panel>
      <p className="muted small">Прайс прислал для известного товара другой CAS. Карточка не менялась — решите, какой CAS верный.</p>
      <table className="table">
        <thead><tr><th>Товар</th><th>CAS карточки</th><th>CAS в прайсе</th><th /></tr></thead>
        <tbody>
          {(list.data?.items ?? []).map((i) => (
            <tr key={i.id}>
              <td>{i.productId ? <Link to={`/products/${i.productId}`}>{i.product}</Link> : i.message}</td>
              <td>{i.currentCas ?? '—'}</td>
              <td>{i.values.cas ?? '—'}</td>
              <td className="num nowrap">
                {can('queues.write') ? (
                  <>
                    <Button size="sm" onClick={() => act.mutate({ id: i.id, action: 'keep' })}>Верен CAS карточки</Button>{' '}
                    <Button size="sm" onClick={() => act.mutate({ id: i.id, action: 'apply' })}>Верен CAS прайса</Button>
                  </>
                ) : null}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      {!list.data?.items.length ? <Empty title="Конфликтов нет" /> : null}
      <Pagination page={page} total={list.data?.total ?? 0} pageSize={50} onPage={setPage} />
    </Panel>
  );
}

function NewBrands() {
  const { can } = useAuth();
  const [target, setTarget] = useState<Record<string, string>>({});
  const [query, setQuery] = useState('');
  const search = useDebounced(query);
  const list = useQuery({ queryKey: ['queue', 'brands'], queryFn: () => api.get<{ items: { id: string; name: string; slug: string; count: number }[] }>('/queues/brands') });
  const pick = useQuery({ queryKey: ['brands-pick', search], queryFn: () => api.get<{ items: { id: string; name: string }[] }>('/brands', { q: search, published: true }), enabled: search.length > 1 });
  const act = useAct<{ id: string; action: string; targetId?: string }>((a) => `/queues/brands/${a.id}`, (a) => ({ action: a.action, targetId: a.targetId }), 'Готово');
  if (list.isLoading) return <Loading />;
  return (
    <Panel>
      <p className="muted small">
        Импорт встретил незнакомое написание и создал бренд без страницы. Это отдельный производитель — «Оставить»; другое написание известного бренда — выберите его и «Объединить»: товары и написание перейдут к нему.
      </p>
      <div className="row" style={{ marginBottom: 10 }}>
        <input className="input" style={{ maxWidth: 300 }} placeholder="Найти бренд для объединения" value={query} onChange={(e) => setQuery(e.target.value)} />
      </div>
      <table className="table">
        <thead><tr><th>Написание в прайсе</th><th className="num">Товаров</th><th>Объединить с</th><th /></tr></thead>
        <tbody>
          {(list.data?.items ?? []).map((b) => (
            <tr key={b.id}>
              <td>{b.name}</td>
              <td className="num">{b.count}</td>
              <td>
                <Select value={target[b.id] ?? ''} options={[{ value: '', label: '—' }, ...(pick.data?.items ?? []).filter((x) => x.id !== b.id).map((x) => ({ value: x.id, label: x.name }))]} onChange={(e) => setTarget({ ...target, [b.id]: e.target.value })} />
              </td>
              <td className="num nowrap">
                {can('queues.write') ? (
                  <>
                    <Button size="sm" onClick={() => act.mutate({ id: b.id, action: 'keep' })}>Оставить</Button>{' '}
                    <Button size="sm" disabled={!target[b.id]} onClick={() => confirm('Перенести товары и написание в выбранный бренд?') && act.mutate({ id: b.id, action: 'merge', targetId: target[b.id] })}>Объединить</Button>
                  </>
                ) : null}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      {!list.data?.items.length ? <Empty title="Новых производителей нет" /> : null}
    </Panel>
  );
}

function Controlled() {
  const { can } = useAuth();
  const list = useQuery({ queryKey: ['queue', 'controlled'], queryFn: () => api.get<{ items: { id: string; catalogNumber: string; name: string; cas: string | null; list: string | null }[] }>('/queues/controlled') });
  const act = useAct<{ id: string; decision: string }>((a) => `/queues/controlled/${a.id}`, (a) => ({ decision: a.decision }), 'Решение сохранено');
  if (list.isLoading) return <Loading />;
  return (
    <Panel>
      <p className="muted small">Совпадение с перечнями ПП № 681 и № 964 только по названию или для солей и меченых форм (ТЗ 5.2.1). Пока химик не решил, позиция скрыта.</p>
      <table className="table">
        <thead><tr><th>Товар</th><th>CAS</th><th>Перечень</th><th /></tr></thead>
        <tbody>
          {(list.data?.items ?? []).map((p) => (
            <tr key={p.id}>
              <td><Link to={`/products/${p.id}`}>{p.catalogNumber}</Link> — {p.name}</td>
              <td>{p.cas ?? '—'}</td>
              <td><Badge tone="bad">{p.list}</Badge></td>
              <td className="num nowrap">
                {can('queues.write') ? (
                  <>
                    <Button size="sm" variant="danger" onClick={() => act.mutate({ id: p.id, decision: 'confirmed' })}>Подконтрольное</Button>{' '}
                    <Button size="sm" onClick={() => act.mutate({ id: p.id, decision: 'cleared' })}>Не подконтрольное</Button>
                  </>
                ) : null}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      {!list.data?.items.length ? <Empty title="Спорных позиций нет" /> : null}
    </Panel>
  );
}

function Enrich() {
  const [page, setPage] = useState(1);
  const list = useQuery({ queryKey: ['queue', 'enrich', page], queryFn: () => api.get<{ total: number; items: { id: string; catalogNumber: string; name: string; completeness: number; views: number; requests: number }[] }>('/queues/enrich', { page }) });
  if (list.isLoading) return <Loading />;
  if (list.error) return <ErrorBox error={list.error} />;
  return (
    <Panel>
      <p className="muted small">Опубликованные карточки ниже порога индексации за 90 дней — сначала те, что чаще смотрят и запрашивают (ТЗ 5.6). Обогащённая карточка уходит в поисковики.</p>
      <table className="table">
        <thead><tr><th>Товар</th><th className="num">Полнота</th><th className="num">Просмотров</th><th className="num">В заявках</th></tr></thead>
        <tbody>
          {(list.data?.items ?? []).map((p) => (
            <tr key={p.id}>
              <td><Link to={`/products/${p.id}`}>{p.catalogNumber}</Link> — {p.name}</td>
              <td className="num">{p.completeness}</td>
              <td className="num">{p.views}</td>
              <td className="num">{p.requests}</td>
            </tr>
          ))}
        </tbody>
      </table>
      {!list.data?.items.length ? <Empty title="Пока пусто">Очередь наполнится, когда посетители начнут открывать карточки.</Empty> : null}
      <Pagination page={page} total={list.data?.total ?? 0} pageSize={50} onPage={setPage} />
    </Panel>
  );
}

function Misses() {
  const [days, setDays] = useState('30');
  const list = useQuery({ queryKey: ['queue', 'misses', days], queryFn: () => api.get<{ items: { query: string; lang: string; count: number; lastAt: string }[] }>('/queues/misses', { days }) });
  return (
    <Panel actions={<Select style={{ width: 160 }} value={days} options={[{ value: '7', label: 'За 7 дней' }, { value: '30', label: 'За 30 дней' }, { value: '90', label: 'За 90 дней' }]} onChange={(e) => setDays(e.target.value)} />} title="Запросы без результатов">
      <p className="muted small">Что искали и не нашли (SRCH-12) — источник для пополнения каталога.</p>
      {list.isLoading ? <Loading /> : (
        <table className="table">
          <thead><tr><th>Запрос</th><th>Язык</th><th className="num">Раз</th><th>Последний</th></tr></thead>
          <tbody>
            {(list.data?.items ?? []).map((m) => (
              <tr key={`${m.query}-${m.lang}`}>
                <td>{m.query}</td>
                <td>{m.lang}</td>
                <td className="num">{m.count}</td>
                <td className="muted nowrap">{formatDate(m.lastAt)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
      {list.data && !list.data.items.length ? <Empty title="Таких запросов не было" /> : null}
    </Panel>
  );
}
