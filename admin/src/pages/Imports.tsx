/**
 * Импорт прайсов (ADM-04, IMP-02, IMP-06): файл → колонки (шаблон сохраняется на источник) → предпросмотр с ошибками
 * → загрузка в фоне с прогрессом → журнал партий, ошибки в xlsx, откат.
 */
import { useEffect, useMemo, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { api, downloadUrl, errorText } from '../api';
import { useAuth } from '../auth';
import { Badge, Button, Empty, ErrorBox, Field, formatDate, Loading, PageHeader, Pagination, Panel, Select, Tabs, TextInput, useToast } from '../ui';

interface Source {
  code: string;
  name: string;
  mapping: Record<string, string>;
  options: Record<string, unknown>;
  builtIn: boolean;
}
interface Batch {
  id: string;
  source: string;
  fileName: string;
  dryRun: boolean;
  status: string;
  rowsDone: number;
  rowsTotal: number;
  counters: Record<string, number>;
  error: string | null;
  author: string;
  startedAt: string;
  finishedAt: string | null;
}
interface Upload {
  id: string;
  fileName: string;
  size: number;
  header: string[];
  sample: (string | null)[][];
  status: string;
  source: string | null;
  dryRun: boolean;
  batchId: string | null;
  error: string | null;
  createdAt: string;
  author: string;
  suggested: { code: string; name: string; matched: string[]; complete: boolean }[];
  batch: Batch | null;
}

const STATUS: Record<string, [string, 'good' | 'warn' | 'bad' | 'info' | 'neutral']> = {
  uploaded: ['загружен', 'neutral'], queued: ['в очереди', 'info'], running: ['идёт', 'info'], done: ['готово', 'good'],
  failed: ['ошибка', 'bad'], rolled_back: ['откачена', 'warn'],
};
const COUNTERS: Record<string, string> = {
  created: 'создано', updated: 'обновлено', unchanged: 'без изменений', skipped: 'пропущено', brands_created: 'новых брендов',
  issues_error: 'ошибок', issues_conflict: 'конфликтов', issues_warning: 'предупреждений', issues_review: 'на проверку',
  packagings_created: 'новых фасовок',
};

export function counterLine(counters: Record<string, number>) {
  return Object.entries(counters).filter(([, v]) => v).map(([k, v]) => `${COUNTERS[k] ?? k} ${v.toLocaleString('ru-RU')}`).join(' · ');
}

export function Imports() {
  const [tab, setTab] = useState<'wizard' | 'journal'>('wizard');
  return (
    <>
      <PageHeader title="Импорт прайсов" description="Позиции, которых нет в каталоге, создаются; существующие обновляются, кроме полей, изменённых вручную (IMP-05). Партию можно откатить." />
      <Tabs value={tab} onChange={setTab} items={[{ key: 'wizard', label: 'Загрузить файл' }, { key: 'journal', label: 'Журнал партий' }]} />
      {tab === 'wizard' ? <Wizard /> : <Journal />}
    </>
  );
}

function Wizard() {
  const { can } = useAuth();
  const toast = useToast();
  const client = useQueryClient();
  const [uploadId, setUploadId] = useState<string | null>(null);
  const [source, setSource] = useState('');
  const [newCode, setNewCode] = useState('');
  const [mapping, setMapping] = useState<Record<string, string>>({});
  const sources = useQuery({ queryKey: ['import-sources'], queryFn: () => api.get<{ items: Source[]; fields: { key: string; name: string; required: boolean }[] }>('/import/sources') });
  const uploads = useQuery({ queryKey: ['import-uploads'], queryFn: () => api.get<Upload[]>('/import/uploads') });
  const upload = useQuery({
    queryKey: ['import-upload', uploadId],
    queryFn: () => api.get<Upload>(`/import/uploads/${uploadId}`),
    enabled: !!uploadId,
    refetchInterval: (q) => (q.state.data && ['queued', 'running'].includes(q.state.data.status) ? 2000 : false),
  });
  const u = upload.data;
  const selected = useMemo(() => sources.data?.items.find((s) => s.code === source), [sources.data, source]);

  useEffect(() => {
    if (u && !source && u.suggested[0]) setSource(u.suggested[0].code);
  }, [u, source]);
  useEffect(() => {
    if (selected) setMapping({ ...selected.mapping });
  }, [selected]);

  const send = useMutation({
    mutationFn: (file: File) => api.upload<Upload>('/import/uploads', file),
    onSuccess: (r) => {
      setUploadId(r.id);
      setSource(r.suggested[0]?.code ?? '');
      void client.invalidateQueries({ queryKey: ['import-uploads'] });
    },
    onError: (e) => toast(errorText(e), 'bad'),
  });
  const run = useMutation({
    mutationFn: async (dryRun: boolean) => {
      const code = source === '__new' ? newCode.trim() : source;
      if (!code) throw new Error('Укажите источник');
      await api.put(`/import/sources/${code}`, { name: selected?.name ?? code, mapping, options: selected?.options ?? {} });
      return api.post<Upload>(`/import/uploads/${uploadId}/run`, { source: code, dryRun });
    },
    onSuccess: (r) => {
      client.setQueryData(['import-upload', uploadId], r);
      void client.invalidateQueries({ queryKey: ['import-sources'] });
    },
    onError: (e) => toast(errorText(e), 'bad'),
  });

  if (!can('import.write')) return <div className="note">Загружать файлы может каталог-менеджер или администратор; журнал партий — во второй вкладке.</div>;
  const fields = sources.data?.fields ?? [];
  const running = !!u && ['queued', 'running'].includes(u.status);

  return (
    <>
      <Panel title="1. Файл">
        <input type="file" accept=".xlsx,.csv" disabled={send.isPending} onChange={(e) => { const file = e.target.files?.[0]; if (file) send.mutate(file); }} />
        <p className="muted small">xlsx или csv до 500 МБ. Первая строка — заголовки колонок.</p>
        {send.isPending ? <Loading text="Загружаем файл…" /> : null}
        {uploads.data?.length && !uploadId ? (
          <>
            <h3 className="mt">Недавние файлы</h3>
            <table className="table">
              <tbody>
                {uploads.data.slice(0, 6).map((x) => (
                  <tr key={x.id} className="clickable" onClick={() => setUploadId(x.id)}>
                    <td>{x.fileName}</td>
                    <td className="muted">{x.author}</td>
                    <td className="muted nowrap">{formatDate(x.createdAt)}</td>
                    <td><Badge tone={STATUS[x.status]?.[1]}>{STATUS[x.status]?.[0] ?? x.status}</Badge></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </>
        ) : null}
      </Panel>
      {u ? (
        <>
          <Panel title={`2. Колонки · ${u.fileName}`}>
            <div className="table-wrap">
              <table className="table">
                <thead><tr>{u.header.map((h, i) => <th key={i}>{h || `—${i + 1}`}</th>)}</tr></thead>
                <tbody>{u.sample.slice(0, 5).map((row, i) => <tr key={i}>{u.header.map((_, j) => <td key={j} className="small">{row[j] ?? ''}</td>)}</tr>)}</tbody>
              </table>
            </div>
            <div className="form-grid mt">
              <Field label="Источник" hint={u.suggested.length ? `Похоже на: ${u.suggested.map((s) => s.name).join(', ')}` : 'Шаблон колонок сохранится на источник'}>
                <Select value={source} options={[{ value: '', label: 'Выберите источник' }, ...(sources.data?.items ?? []).map((s) => ({ value: s.code, label: s.name })), { value: '__new', label: '+ Новый поставщик' }]} onChange={(e) => setSource(e.target.value)} />
              </Field>
              {source === '__new' ? (
                <Field label="Код нового источника" hint="Латиница, например supplier-x">
                  <TextInput value={newCode} onChange={(e) => setNewCode(e.target.value)} />
                </Field>
              ) : null}
            </div>
            <div className="form-grid mt">
              {fields.map((f) => (
                <Field key={f.key} label={`${f.name}${f.required ? ' *' : ''}`}>
                  <Select value={mapping[f.key] ?? ''} options={[{ value: '', label: '— нет —' }, ...u.header.filter(Boolean).map((h) => ({ value: h, label: h }))]} onChange={(e) => setMapping({ ...mapping, [f.key]: e.target.value })} />
                </Field>
              ))}
            </div>
          </Panel>
          <Panel title="3. Предпросмотр и загрузка">
            <div className="row">
              <Button busy={run.isPending && run.variables === true} disabled={running || !source} onClick={() => run.mutate(true)}>
                Предпросмотр (без записи)
              </Button>
              <Button variant="primary" busy={run.isPending && run.variables === false} disabled={running || !source} onClick={() => confirm('Загрузить файл в каталог?') && run.mutate(false)}>
                Загрузить в каталог
              </Button>
              <Badge tone={STATUS[u.status]?.[1]}>{STATUS[u.status]?.[0] ?? u.status}</Badge>
            </div>
            {u.error ? <div className="error-box mt">{u.error}</div> : null}
            {u.batch ? (
              <div className="mt">
                <p>
                  {u.batch.dryRun ? 'Предпросмотр' : 'Загрузка'}: строк {u.batch.rowsDone.toLocaleString('ru-RU')} — {counterLine(u.batch.counters) || 'идёт…'}
                </p>
                <Link to={`/import/batches/${u.batch.id}`}>Ошибки и конфликты партии →</Link>
              </div>
            ) : running ? <Loading text="Идёт обработка: страница обновится сама" /> : null}
          </Panel>
        </>
      ) : null}
    </>
  );
}

function Journal() {
  const navigate = useNavigate();
  const [page, setPage] = useState(1);
  const list = useQuery({ queryKey: ['import-batches', page], queryFn: () => api.get<{ total: number; items: Batch[] }>('/import/batches', { page }), refetchInterval: 5000 });
  if (list.isLoading) return <Loading />;
  return (
    <div className="panel table-wrap">
      <table className="table">
        <thead><tr><th>Начата</th><th>Файл</th><th>Источник</th><th>Кто</th><th>Состояние</th><th>Итог</th></tr></thead>
        <tbody>
          {(list.data?.items ?? []).map((b) => (
            <tr key={b.id} className="clickable" onClick={() => navigate(`/import/batches/${b.id}`)}>
              <td className="nowrap">{formatDate(b.startedAt)}</td>
              <td>{b.fileName} {b.dryRun ? <Badge>предпросмотр</Badge> : null}</td>
              <td>{b.source}</td>
              <td className="muted">{b.author}</td>
              <td><Badge tone={STATUS[b.status]?.[1]}>{STATUS[b.status]?.[0] ?? b.status}</Badge></td>
              <td className="small">{counterLine(b.counters)}</td>
            </tr>
          ))}
        </tbody>
      </table>
      {!list.data?.items.length ? <Empty title="Партий ещё не было" /> : null}
      <Pagination page={page} total={list.data?.total ?? 0} pageSize={30} onPage={setPage} />
    </div>
  );
}

interface BatchCard extends Batch {
  summary: { kind: string; code: string; count: number }[];
  issues: { id: number; row: number; kind: string; code: string; message: string; productId: string | null; resolved: boolean }[];
}

export function Batch() {
  const { id = '' } = useParams();
  const { can } = useAuth();
  const toast = useToast();
  const client = useQueryClient();
  const [kind, setKind] = useState('');
  const [page, setPage] = useState(1);
  const card = useQuery({ queryKey: ['import-batch', id, kind, page], queryFn: () => api.get<BatchCard>(`/import/batches/${id}`, { kind, page }), refetchInterval: (q) => (q.state.data?.status === 'running' ? 3000 : false) });
  const rollback = useMutation({
    mutationFn: () => api.post<{ deleted: number; restored: number }>(`/import/batches/${id}/rollback`),
    onSuccess: (r) => {
      toast(`Откачено: удалено ${r.deleted}, восстановлено ${r.restored}`);
      void client.invalidateQueries({ queryKey: ['import-batch', id] });
    },
    onError: (e) => toast(errorText(e), 'bad'),
  });
  if (card.isLoading) return <Loading />;
  if (!card.data) return <ErrorBox error={card.error} />;
  const b = card.data;
  const total = b.summary.filter((s) => !kind || s.kind === kind).reduce((a, s) => a + s.count, 0);
  return (
    <>
      <PageHeader
        title={`Партия: ${b.fileName}`}
        description={<><Link to="/import">← Импорт</Link> · {b.source} · {b.author} · {formatDate(b.startedAt)} — {formatDate(b.finishedAt)}</>}
        actions={
          <>
            <a className="btn" href={downloadUrl(`/import/batches/${id}/issues.xlsx`)}>Ошибки в xlsx</a>
            {can('import.write') && !b.dryRun && b.status === 'done' ? (
              <Button variant="danger" busy={rollback.isPending} onClick={() => confirm('Откатить партию? Созданные ею товары удалятся, изменённые получат прежние значения') && rollback.mutate()}>
                Откатить партию
              </Button>
            ) : null}
          </>
        }
      />
      <Panel>
        <p>
          <Badge tone={STATUS[b.status]?.[1]}>{STATUS[b.status]?.[0] ?? b.status}</Badge> {b.dryRun ? <Badge>предпросмотр: каталог не менялся</Badge> : null} · строк {b.rowsDone.toLocaleString('ru-RU')}
        </p>
        <p>{counterLine(b.counters)}</p>
        {b.error ? <div className="error-box">{b.error}</div> : null}
      </Panel>
      <Panel title="Замечания">
        <div className="row" style={{ marginBottom: 10 }}>
          <Button size="sm" variant={kind ? 'ghost' : 'secondary'} onClick={() => { setKind(''); setPage(1); }}>Все</Button>
          {[...new Set(b.summary.map((s) => s.kind))].map((k) => (
            <Button key={k} size="sm" variant={kind === k ? 'secondary' : 'ghost'} onClick={() => { setKind(k); setPage(1); }}>{k}</Button>
          ))}
        </div>
        <p className="muted small">{b.summary.map((s) => `${s.code}: ${s.count}`).join(' · ')}</p>
        <table className="table">
          <thead><tr><th className="num">Строка</th><th>Вид</th><th>Код</th><th>Что не так</th></tr></thead>
          <tbody>
            {b.issues.map((i) => (
              <tr key={i.id}>
                <td className="num">{i.row}</td>
                <td>{i.kind}</td>
                <td className="small">{i.code}</td>
                <td>{i.message} {i.productId ? <Link to={`/products/${i.productId}`}>товар →</Link> : null} {i.resolved ? <Badge tone="good">решено</Badge> : null}</td>
              </tr>
            ))}
          </tbody>
        </table>
        {!b.issues.length ? <Empty title="Замечаний нет" /> : null}
        <Pagination page={page} total={total} pageSize={100} onPage={setPage} />
      </Panel>
    </>
  );
}
