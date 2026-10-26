/** Журнал заявок сайта и подписчики (ADM-08). Контакты и состав видит только администратор. */
import { useState } from 'react';
import { useSearchParams } from 'react-router';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { api, downloadUrl, errorText } from '../api';
import { useAuth } from '../auth';
import { Badge, Button, Empty, ErrorBox, formatDate, Loading, Modal, PageHeader, Pagination, Select, TextInput, useDebounced, useToast } from '../ui';

interface RequestRow {
  id: string;
  number: string;
  kindName: string;
  lang: string;
  createdAt: string;
  status: string;
  crmNumber: string | null;
  deliveredAt: string | null;
  deliveryError: string | null;
  suspicious: boolean;
  items: number;
  company: string;
  customer: string;
  email: string;
  phone: string;
  channel: string | null;
  crmStatus: string | null;
  crmStage: string | null;
  crmRequestNumber: string | null;
  sale: { amount: string; currency: string | null } | null;
}

const STATUS: Record<string, [string, 'good' | 'warn' | 'bad']> = {
  delivered: ['в CRM', 'good'], accepted: ['ждёт доставки', 'warn'], failed: ['не доставлена', 'bad'],
};

// What the CRM reported back (flow F2): the fate of the site request and the stage of the CRM request made from it.
const CRM_STATUS: Record<string, string> = { in_work: 'в работе', converted: 'преобразована', rejected: 'отклонена' };
const CRM_STAGE: Record<string, string> = {
  new: 'новая', clarification: 'уточнение', collecting_quotes: 'сбор квот', quote_given: 'квота получена',
  calculation: 'расчёт', proposal_sent: 'КП отправлено', composition_agreed: 'состав согласован',
  awaiting_payment: 'ждёт оплаты', sale_confirmed: 'продажа', lost: 'проиграна',
};

function money(sale: RequestRow['sale']) {
  return sale ? `${Number(sale.amount).toLocaleString('ru-RU', { maximumFractionDigits: 0 })} ${sale.currency === 'RUB' || !sale.currency ? '₽' : sale.currency}` : '';
}

function CrmProgress({ r }: { r: RequestRow }) {
  if (!r.crmStatus && !r.crmStage) return <span className="muted">—</span>;
  return (
    <>
      {r.crmStage ? <Badge tone={r.crmStage === 'sale_confirmed' ? 'good' : r.crmStage === 'lost' ? 'bad' : 'info'}>{CRM_STAGE[r.crmStage] ?? r.crmStage}</Badge>
        : <Badge tone={r.crmStatus === 'rejected' ? 'bad' : 'info'}>{CRM_STATUS[r.crmStatus ?? ''] ?? r.crmStatus}</Badge>}
      {r.crmRequestNumber ? <div className="muted small">{r.crmRequestNumber}</div> : null}
      {r.sale ? <div className="small">{money(r.sale)}</div> : null}
    </>
  );
}

export function Requests() {
  const [params, setParams] = useSearchParams();
  const [q, setQ] = useState('');
  const [page, setPage] = useState(1);
  const [open, setOpen] = useState<string | null>(null);
  const search = useDebounced(q);
  const status = params.get('status') ?? '';
  const list = useQuery({ queryKey: ['requests', status, search, page], queryFn: () => api.get<{ total: number; counts: Record<string, number>; pii: boolean; items: RequestRow[] }>('/requests', { status, q: search, page }), refetchInterval: 30_000 });
  return (
    <>
      <PageHeader title="Журнал заявок" description="Каждая заявка сначала сохраняется на сайте, потом уходит в CRM через очередь с повторами (RFQ-07)." />
      <div className="filters">
        <TextInput placeholder={list.data?.pii ? 'Номер, компания, почта, телефон, ИНН' : 'Номер заявки или номер CRM'} value={q} onChange={(e) => { setQ(e.target.value); setPage(1); }} />
        <Select value={status} options={[{ value: '', label: 'Все заявки' }, ...Object.entries(STATUS).map(([k, v]) => ({ value: k, label: `${v[0]} · ${list.data?.counts[k] ?? 0}` }))]} onChange={(e) => { setParams(e.target.value ? { status: e.target.value } : {}); setPage(1); }} />
      </div>
      {list.data && !list.data.pii ? <div className="note">Контакты и компании скрыты: персональные данные видит администратор (ADM-08).</div> : null}
      <ErrorBox error={list.error} />
      {list.isLoading ? <Loading /> : (
        <div className="panel table-wrap">
          <table className="table">
            <thead><tr><th>Номер</th><th>Когда</th><th>Тип</th><th>Компания</th><th>Контакт</th><th className="num">Позиций</th><th>Доставка</th><th>В CRM</th><th>Канал</th></tr></thead>
            <tbody>
              {(list.data?.items ?? []).map((r) => (
                <tr key={r.id} className="clickable" onClick={() => setOpen(r.id)}>
                  <td className="nowrap">{r.number} {r.suspicious ? <Badge tone="warn">антиспам</Badge> : null}</td>
                  <td className="nowrap">{formatDate(r.createdAt)}</td>
                  <td>{r.kindName}{r.lang === 'en' ? ' · EN' : ''}</td>
                  <td>{r.company}</td>
                  <td>{r.customer}<div className="muted small">{r.email}</div></td>
                  <td className="num">{r.items}</td>
                  <td className="nowrap">
                    <Badge tone={STATUS[r.status]?.[1]}>{STATUS[r.status]?.[0] ?? r.status}</Badge>
                    {r.crmNumber ? <div className="muted small">{r.crmNumber}</div> : null}
                    {r.deliveryError ? <div className="small" style={{ color: 'var(--danger)' }}>{r.deliveryError}</div> : null}
                  </td>
                  <td className="nowrap"><CrmProgress r={r} /></td>
                  <td className="muted">{r.channel ?? '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
          {!list.data?.items.length ? <Empty title="Заявок нет" /> : null}
          <Pagination page={page} total={list.data?.total ?? 0} pageSize={50} onPage={setPage} />
        </div>
      )}
      {open ? <RequestCard id={open} onClose={() => setOpen(null)} /> : null}
    </>
  );
}

interface Card extends RequestRow {
  attempts: { attempt: number; at: string; outcome: string; statusCode: number | null; error: string | null; durationMs: number }[];
  attachments: { name: string; size: number }[];
  pageUrl: string | null;
  attribution: Record<string, unknown> | null;
  inn?: string | null;
  city?: string | null;
  comment?: string | null;
  positions?: { name: string; brand: string | null; catalogNumber: string | null; cas: string | null; packaging: string | null; quantity: string; unit: string; analogue: string; comment: string | null }[];
}

function RequestCard({ id, onClose }: { id: string; onClose: () => void }) {
  const { can } = useAuth();
  const toast = useToast();
  const client = useQueryClient();
  const card = useQuery({ queryKey: ['request', id], queryFn: () => api.get<Card>(`/requests/${id}`) });
  const resend = useMutation({
    mutationFn: () => api.post<{ message: string }>(`/requests/${id}/resend`),
    onSuccess: (r) => {
      toast(r.message);
      void client.invalidateQueries({ queryKey: ['requests'] });
      void client.invalidateQueries({ queryKey: ['request', id] });
    },
    onError: (e) => toast(errorText(e), 'bad'),
  });
  const c = card.data;
  return (
    <Modal title={c ? `Заявка ${c.number}` : 'Заявка'} onClose={onClose} wide>
      {!c ? <Loading /> : (
        <div className="stack">
          <div className="row">
            <Badge tone={STATUS[c.status]?.[1]}>{STATUS[c.status]?.[0] ?? c.status}</Badge>
            {c.crmNumber ? <span>в CRM: <strong>{c.crmNumber}</strong> ({formatDate(c.deliveredAt)})</span> : null}
            {c.crmStatus || c.crmStage ? <span>· в работе CRM: <CrmProgress r={c} /></span> : null}
            {can('requests.resend') && c.status !== 'delivered' ? <Button size="sm" busy={resend.isPending} onClick={() => resend.mutate()}>Отправить в CRM повторно</Button> : null}
          </div>
          <div className="grid-2">
            <div>
              <p><strong>{c.company}</strong>{c.inn ? ` · ИНН ${c.inn}` : ''}</p>
              <p>{c.customer} · {c.phone} · {c.email}{c.city ? ` · ${c.city}` : ''}</p>
              {c.comment ? <p className="muted">{c.comment}</p> : null}
            </div>
            <div className="muted small">
              <p>{c.kindName} · {formatDate(c.createdAt)} · канал {c.channel ?? '—'}</p>
              {c.pageUrl ? <p>Страница: {c.pageUrl}</p> : null}
            </div>
          </div>
          {c.positions ? (
            <table className="table">
              <thead><tr><th>Позиция</th><th>Кат. №</th><th>CAS</th><th>Фасовка</th><th className="num">Кол-во</th><th>Аналоги</th></tr></thead>
              <tbody>
                {c.positions.map((p, i) => (
                  <tr key={i}><td>{p.name}{p.brand ? <div className="muted small">{p.brand}</div> : null}</td><td>{p.catalogNumber}</td><td>{p.cas}</td><td>{p.packaging}</td><td className="num">{p.quantity} {p.unit}</td><td>{p.analogue}</td></tr>
                ))}
              </tbody>
            </table>
          ) : <p className="muted">Состав заявки виден администратору.</p>}
          {c.attachments.length ? <p className="small">Вложения: {c.attachments.map((a) => a.name).join(', ')}</p> : null}
          <h3>Попытки доставки</h3>
          <table className="table">
            <tbody>
              {c.attempts.map((a) => (
                <tr key={a.attempt}><td>№ {a.attempt}</td><td className="nowrap">{formatDate(a.at)}</td><td>{a.outcome}</td><td>{a.statusCode ?? '—'}</td><td className="muted">{a.error ?? ''}</td><td className="num">{a.durationMs} мс</td></tr>
              ))}
            </tbody>
          </table>
          {!c.attempts.length ? <p className="muted small">Попыток ещё не было: доставка в CRM выключена или очередь не дошла.</p> : null}
        </div>
      )}
    </Modal>
  );
}

export function Subscribers() {
  const [q, setQ] = useState('');
  const [status, setStatus] = useState('');
  const [page, setPage] = useState(1);
  const search = useDebounced(q);
  const list = useQuery({ queryKey: ['subscribers', search, status, page], queryFn: () => api.get<{ total: number; counts: Record<string, number>; items: { id: string; email: string; lang: string; status: string; source: string | null; consentAt: string; unsubscribedAt: string | null; inCrm: boolean }[] }>('/subscribers', { q: search, status, page }) });
  return (
    <>
      <PageHeader
        title="Подписчики"
        description="Адреса с двумя согласиями — на обработку ПДн и на рассылку (NFR-07). Каждый подписчик передаётся в CRM как контакт для рассылки."
        actions={<><a className="btn" href={downloadUrl('/subscribers/export')}>CSV активных</a><a className="btn" href={downloadUrl('/subscribers/export', { all: true })}>CSV всех</a></>}
      />
      <div className="filters">
        <TextInput placeholder="Почта" value={q} onChange={(e) => { setQ(e.target.value); setPage(1); }} />
        <Select value={status} options={[{ value: '', label: 'Все' }, { value: 'active', label: `Подписаны · ${list.data?.counts.active ?? 0}` }, { value: 'unsubscribed', label: `Отписались · ${list.data?.counts.unsubscribed ?? 0}` }]} onChange={(e) => { setStatus(e.target.value); setPage(1); }} />
      </div>
      {list.isLoading ? <Loading /> : (
        <div className="panel table-wrap">
          <table className="table">
            <thead><tr><th>Почта</th><th>Язык</th><th>Состояние</th><th>Согласие</th><th>Источник</th><th>CRM</th></tr></thead>
            <tbody>
              {(list.data?.items ?? []).map((s) => (
                <tr key={s.id}>
                  <td>{s.email}</td>
                  <td>{s.lang}</td>
                  <td>{s.status === 'active' ? <Badge tone="good">подписан</Badge> : <Badge>отписался {formatDate(s.unsubscribedAt, false)}</Badge>}</td>
                  <td className="nowrap muted">{formatDate(s.consentAt)}</td>
                  <td className="muted">{s.source ?? '—'}</td>
                  <td>{s.inCrm ? <Badge tone="info">передан</Badge> : <span className="muted">ждёт</span>}</td>
                </tr>
              ))}
            </tbody>
          </table>
          {!list.data?.items.length ? <Empty title="Подписчиков нет" /> : null}
          <Pagination page={page} total={list.data?.total ?? 0} pageSize={100} onPage={setPage} />
        </div>
      )}
    </>
  );
}
