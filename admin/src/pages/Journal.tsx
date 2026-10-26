/** Журнал всех изменений (ADM-01): кто, когда и что изменил, состояние до и после. */
import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { api } from '../api';
import type { HistoryEntry } from '../types';
import { Empty, formatDate, Loading, Modal, PageHeader, Pagination, Select, TextInput, useDebounced } from '../ui';

const ENTITIES = [
  ['', 'Всё'], ['product', 'Товары'], ['page', 'Страницы'], ['category', 'Разделы'], ['brand', 'Бренды'], ['substance', 'Субстанции'],
  ['landing', 'Посадочные'], ['redirect', 'Редиректы'], ['setting', 'Настройки'], ['import', 'Импорт'], ['request', 'Заявки'], ['staff', 'Сотрудники'],
];

export function Journal() {
  const [entity, setEntity] = useState('');
  const [actor, setActor] = useState('');
  const [q, setQ] = useState('');
  const [page, setPage] = useState(1);
  const [open, setOpen] = useState<number | null>(null);
  const a = useDebounced(actor);
  const s = useDebounced(q);
  const list = useQuery({ queryKey: ['audit', entity, a, s, page], queryFn: () => api.get<{ total: number; items: HistoryEntry[] }>('/audit', { entity, actor: a, q: s, page }) });
  const entry = useQuery({ queryKey: ['audit-entry', open], queryFn: () => api.get<HistoryEntry>(`/audit/${open}`), enabled: open !== null });
  return (
    <>
      <PageHeader title="Журнал изменений" description="Все действия в админке. Версию страницы или карточки можно вернуть из её истории." />
      <div className="filters">
        <Select value={entity} options={ENTITIES.map(([value, label]) => ({ value, label }))} onChange={(e) => { setEntity(e.target.value); setPage(1); }} />
        <TextInput placeholder="Сотрудник" value={actor} onChange={(e) => { setActor(e.target.value); setPage(1); }} />
        <TextInput placeholder="Что изменено" value={q} onChange={(e) => { setQ(e.target.value); setPage(1); }} />
      </div>
      {list.isLoading ? <Loading /> : (
        <div className="panel table-wrap">
          <table className="table">
            <thead><tr><th>Когда</th><th>Кто</th><th>Что</th><th>Действие</th><th>Изменения</th></tr></thead>
            <tbody>
              {(list.data?.items ?? []).map((h) => (
                <tr key={h.id} className="clickable" onClick={() => setOpen(h.id)}>
                  <td className="nowrap">{formatDate(h.at)}</td>
                  <td>{h.actor}</td>
                  <td>{ENTITIES.find(([k]) => k === h.entity)?.[1] ?? h.entity}</td>
                  <td>{h.action}</td>
                  <td className="muted">{h.summary}</td>
                </tr>
              ))}
            </tbody>
          </table>
          {!list.data?.items.length ? <Empty title="Записей нет" /> : null}
          <Pagination page={page} total={list.data?.total ?? 0} pageSize={100} onPage={setPage} />
        </div>
      )}
      {open !== null ? (
        <Modal title="Запись журнала" onClose={() => setOpen(null)} wide>
          {!entry.data ? <Loading /> : (
            <div className="stack">
              <p>{formatDate(entry.data.at)} · {entry.data.actor} · {entry.data.action} · {entry.data.summary}</p>
              <div className="diff">
                <div><div className="field-label">До</div><pre>{JSON.stringify(entry.data.before, null, 2) ?? '—'}</pre></div>
                <div><div className="field-label">После</div><pre>{JSON.stringify(entry.data.after, null, 2) ?? '—'}</pre></div>
              </div>
            </div>
          )}
        </Modal>
      ) : null}
    </>
  );
}
