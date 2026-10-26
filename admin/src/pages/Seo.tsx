/** SEO (ADM-07): посадочные из срезов фильтров, редиректы, шаблоны метатегов, robots.txt, отчёт о дублях. */
import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Plus, Trash2 } from 'lucide-react';
import { api, downloadUrl, errorText } from '../api';
import { useAuth } from '../auth';
import type { EditorView } from '../types';
import { Badge, Button, Empty, ErrorBox, Field, formatDate, Loading, Modal, PageHeader, Pagination, Panel, Select, TextArea, TextInput, useDebounced, useToast } from '../ui';

interface LandingRow {
  id: string;
  categoryPath: string;
  slug: string;
  filters: Record<string, string[]>;
  name: string;
  status: string;
  hasEn: boolean;
  hasDraft: boolean;
  path: string;
}

export function Landings() {
  const { can } = useAuth();
  const navigate = useNavigate();
  const toast = useToast();
  const [form, setForm] = useState<{ categoryPath: string; slug: string; name: string; brand: string } | null>(null);
  const list = useQuery({ queryKey: ['landings'], queryFn: () => api.get<{ items: LandingRow[] }>('/landings') });
  const create = useMutation({
    mutationFn: () => api.post<EditorView>('/landings', { categoryPath: form?.categoryPath, slug: form?.slug, name: form?.name, filters: form?.brand ? { brand: [form.brand] } : {} }),
    onSuccess: (r) => navigate(`/edit/landing/${r.id}`),
    onError: (e) => toast(errorText(e), 'bad'),
  });
  if (list.isLoading) return <Loading />;
  return (
    <>
      <PageHeader
        title="SEO-посадочные"
        description="Срезы фильтров раздела со своим адресом, H1, Title и текстом (URL-07). Индексируются, когда в срезе не меньше 3 позиций."
        actions={can('seo.write') ? <Button variant="primary" onClick={() => setForm({ categoryPath: '', slug: '', name: '', brand: '' })}><Plus size={15} /> Посадочная</Button> : null}
      />
      <ErrorBox error={list.error} />
      <div className="panel table-wrap">
        <table className="table">
          <thead>
            <tr>
              <th>Название</th>
              <th>Адрес</th>
              <th>Фильтры</th>
              <th>Состояние</th>
            </tr>
          </thead>
          <tbody>
            {(list.data?.items ?? []).map((l) => (
              <tr key={l.id} className="clickable" onClick={() => navigate(`/edit/landing/${l.id}`)}>
                <td>{l.name}</td>
                <td><code>{l.path}</code></td>
                <td className="muted small">{Object.entries(l.filters).map(([k, v]) => `${k}: ${v.join(', ')}`).join(' · ')}</td>
                <td className="nowrap">
                  {l.status === 'published' ? <Badge tone="good">опубликована</Badge> : <Badge>скрыта</Badge>} {l.hasEn ? <Badge tone="good">EN</Badge> : null} {l.hasDraft ? <Badge tone="warn">черновик</Badge> : null}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {form ? (
        <Modal title="Новая SEO-посадочная" onClose={() => setForm(null)}>
          <div className="stack">
            <Field label="Раздел каталога" hint="Например chromatography/hplc-columns">
              <TextInput value={form.categoryPath} onChange={(e) => setForm({ ...form, categoryPath: e.target.value })} />
            </Field>
            <Field label="Адрес среза" hint="Например phenomenex-c18">
              <TextInput value={form.slug} onChange={(e) => setForm({ ...form, slug: e.target.value })} />
            </Field>
            <Field label="Короткая подпись (чипы «Подборки»)">
              <TextInput value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
            </Field>
            <Field label="Бренд среза (адрес бренда, необязательно)" hint="Остальные фильтры — в редакторе">
              <TextInput value={form.brand} onChange={(e) => setForm({ ...form, brand: e.target.value })} />
            </Field>
            <div className="row row-end">
              <Button variant="primary" busy={create.isPending} disabled={!form.categoryPath || !form.slug || !form.name} onClick={() => create.mutate()}>
                Создать
              </Button>
            </div>
          </div>
        </Modal>
      ) : null}
    </>
  );
}

interface RedirectRow {
  id: string;
  source: string;
  target: string;
  code: number;
  note: string | null;
  updatedAt: string | null;
}

export function Redirects() {
  const { can } = useAuth();
  const toast = useToast();
  const client = useQueryClient();
  const [q, setQ] = useState('');
  const [page, setPage] = useState(1);
  const [edit, setEdit] = useState<Partial<RedirectRow> | null>(null);
  const [csv, setCsv] = useState<string | null>(null);
  const search = useDebounced(q);
  const writable = can('seo.write');
  const list = useQuery({ queryKey: ['redirects', search, page], queryFn: () => api.get<{ total: number; items: RedirectRow[] }>('/redirects', { q: search, page }) });
  const check = useQuery({ queryKey: ['redirects-check'], queryFn: () => api.get<{ total: number; problems: { source: string; target: string; problem: string }[] }>('/redirects/check') });
  const refresh = () => {
    void client.invalidateQueries({ queryKey: ['redirects'] });
    void client.invalidateQueries({ queryKey: ['redirects-check'] });
  };
  const save = useMutation({
    mutationFn: () => (edit?.id ? api.put(`/redirects/${edit.id}`, edit) : api.post('/redirects', edit)),
    onSuccess: () => {
      setEdit(null);
      refresh();
      toast('Сохранено — сайт применит редирект в течение минуты');
    },
    onError: (e) => toast(errorText(e), 'bad'),
  });
  const remove = useMutation({ mutationFn: (id: string) => api.delete(`/redirects/${id}`), onSuccess: refresh });
  const importCsv = useMutation({
    mutationFn: () => api.post<{ created: number; updated: number; errors: string[] }>('/redirects/import', { csv }),
    onSuccess: (r) => {
      setCsv(null);
      refresh();
      toast(`Добавлено ${r.created}, изменено ${r.updated}${r.errors.length ? `, ошибок ${r.errors.length}: ${r.errors.slice(0, 3).join('; ')}` : ''}`, r.errors.length ? 'bad' : 'good');
    },
    onError: (e) => toast(errorText(e), 'bad'),
  });
  return (
    <>
      <PageHeader
        title="Редиректы"
        description="301 — страница переехала навсегда, 302 — временно (URL-11). Цепочки сразу сокращаются до одного перехода, петли не сохраняются."
        actions={
          <>
            <a className="btn" href={downloadUrl('/redirects/export')}>Скачать CSV</a>
            {writable ? <Button onClick={() => setCsv('')}>Загрузить CSV</Button> : null}
            {writable ? <Button variant="primary" onClick={() => setEdit({ code: 301 })}><Plus size={15} /> Редирект</Button> : null}
          </>
        }
      />
      {check.data?.problems.length ? (
        <div className="warn-box">
          Проблемы: {check.data.problems.map((p) => `${p.source} — ${p.problem}`).join('; ')}
        </div>
      ) : null}
      <div className="filters">
        <TextInput placeholder="Поиск по адресу" value={q} onChange={(e) => { setQ(e.target.value); setPage(1); }} />
      </div>
      {list.isLoading ? <Loading /> : (
        <div className="panel table-wrap">
          <table className="table">
            <thead>
              <tr><th>Откуда</th><th>Куда</th><th>Код</th><th>Заметка</th><th>Изменён</th><th /></tr>
            </thead>
            <tbody>
              {(list.data?.items ?? []).map((r) => (
                <tr key={r.id} className={writable ? 'clickable' : undefined} onClick={() => writable && setEdit(r)}>
                  <td><code>{r.source}</code></td>
                  <td><code>{r.target}</code></td>
                  <td>{r.code}</td>
                  <td className="muted small">{r.note}</td>
                  <td className="muted nowrap">{formatDate(r.updatedAt, false)}</td>
                  <td className="num" onClick={(e) => e.stopPropagation()}>
                    {writable ? <button type="button" className="icon-btn" aria-label="Удалить" onClick={() => confirm(`Удалить редирект с ${r.source}?`) && remove.mutate(r.id)}><Trash2 size={15} /></button> : null}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {!list.data?.items.length ? <Empty title="Редиректов нет" /> : null}
          <Pagination page={page} total={list.data?.total ?? 0} pageSize={100} onPage={setPage} />
        </div>
      )}
      {edit ? (
        <Modal title={edit.id ? 'Редирект' : 'Новый редирект'} onClose={() => setEdit(null)}>
          <div className="stack">
            <Field label="Откуда" hint="Путь сайта, например /old-page/ — домен и параметры отбросятся">
              <TextInput value={edit.source ?? ''} onChange={(e) => setEdit({ ...edit, source: e.target.value })} />
            </Field>
            <Field label="Куда" hint="Путь сайта или полный адрес">
              <TextInput value={edit.target ?? ''} onChange={(e) => setEdit({ ...edit, target: e.target.value })} />
            </Field>
            <Field label="Код">
              <Select value={String(edit.code ?? 301)} options={[{ value: '301', label: '301 — навсегда' }, { value: '302', label: '302 — временно' }]} onChange={(e) => setEdit({ ...edit, code: Number(e.target.value) })} />
            </Field>
            <Field label="Заметка">
              <TextInput value={edit.note ?? ''} onChange={(e) => setEdit({ ...edit, note: e.target.value })} />
            </Field>
            <div className="row row-end">
              <Button variant="primary" busy={save.isPending} onClick={() => save.mutate()}>Сохранить</Button>
            </div>
          </div>
        </Modal>
      ) : null}
      {csv !== null ? (
        <Modal title="Загрузить редиректы из CSV" onClose={() => setCsv(null)}>
          <div className="stack">
            <p className="muted small">Строки «откуда;куда;код» — код необязателен (301). Можно вставить текст или выбрать файл.</p>
            <input type="file" accept=".csv,text/csv" onChange={async (e) => { const file = e.target.files?.[0]; if (file) setCsv(await file.text()); }} />
            <TextArea rows={10} value={csv} onChange={(e) => setCsv(e.target.value)} placeholder={'/old/;/new/;301'} />
            <div className="row row-end">
              <Button variant="primary" busy={importCsv.isPending} disabled={!csv.trim()} onClick={() => importCsv.mutate()}>Загрузить</Button>
            </div>
          </div>
        </Modal>
      ) : null}
    </>
  );
}

type Templates = Record<'product' | 'substance', Record<'ru' | 'en', Record<string, string>>>;

export function SeoRules() {
  const { can } = useAuth();
  const toast = useToast();
  const writable = can('seo.write');
  const templates = useQuery({ queryKey: ['seo-templates'], queryFn: () => api.get<{ value: Templates; placeholders: Record<string, string[]> }>('/seo/templates') });
  const robots = useQuery({ queryKey: ['seo-robots'], queryFn: () => api.get<{ extra: string }>('/seo/robots') });
  const [value, setValue] = useState<Templates | null>(null);
  const [extra, setExtra] = useState('');
  useEffect(() => { if (templates.data) setValue(structuredClone(templates.data.value)); }, [templates.data]);
  useEffect(() => { if (robots.data) setExtra(robots.data.extra); }, [robots.data]);
  const saveTemplates = useMutation({ mutationFn: () => api.put('/seo/templates', { value }), onSuccess: () => toast('Шаблоны сохранены'), onError: (e) => toast(errorText(e), 'bad') });
  const saveRobots = useMutation({ mutationFn: () => api.put('/seo/robots', { extra }), onSuccess: () => toast('robots.txt обновлён'), onError: (e) => toast(errorText(e), 'bad') });
  if (!value || templates.isLoading) return <Loading />;
  const field = (kind: 'product' | 'substance', lang: 'ru' | 'en', name: string, label: string) => (
    <Field label={`${label} ${lang.toUpperCase()}`}>
      <TextInput value={value[kind]?.[lang]?.[name] ?? ''} disabled={!writable} onChange={(e) => setValue({ ...value, [kind]: { ...value[kind], [lang]: { ...value[kind]?.[lang], [name]: e.target.value } } })} placeholder="Пусто — шаблон ТЗ 10.2" />
    </Field>
  );
  return (
    <>
      <PageHeader title="Шаблоны и robots.txt" description="Метатеги карточек и субстанций по шаблону с ручным переопределением на карточке (SEO-02); дополнение robots.txt (SEO-03)." />
      <Panel title="Карточка товара" actions={<span className="muted small">{templates.data?.placeholders.product.join(' ')}</span>}>
        <div className="form-grid">
          {(['ru', 'en'] as const).flatMap((lang) => [field('product', lang, 'title', 'Title'), field('product', lang, 'titleNoCas', 'Title без CAS'), field('product', lang, 'description', 'Description')])}
        </div>
      </Panel>
      <Panel title="Субстанция" actions={<span className="muted small">{templates.data?.placeholders.substance.join(' ')}</span>}>
        <div className="form-grid">
          {(['ru', 'en'] as const).flatMap((lang) => [field('substance', lang, 'title', 'Title'), field('substance', lang, 'description', 'Description')])}
        </div>
      </Panel>
      {writable ? <div className="row row-end" style={{ marginBottom: 16 }}><Button variant="primary" busy={saveTemplates.isPending} onClick={() => saveTemplates.mutate()}>Сохранить шаблоны</Button></div> : null}
      <Panel title="Дополнение robots.txt">
        <p className="muted small">Обязательные правила (закрыты /search/, /rfq/, /api/ и т. д., Clean-param, Sitemap) сайт пишет сам. Здесь — дополнительные строки Disallow/Allow; основные разделы закрыть нельзя.</p>
        <TextArea rows={6} value={extra} disabled={!writable} onChange={(e) => setExtra(e.target.value)} placeholder={'Disallow: /print/'} />
        {writable ? <div className="row row-end mt"><Button busy={saveRobots.isPending} onClick={() => saveRobots.mutate()}>Сохранить robots.txt</Button></div> : null}
      </Panel>
    </>
  );
}

interface Report {
  duplicates: { field: string; lang: string; value: string; pages: string[] }[];
  indexing: { products: Record<string, number>; indexable: number; pagesHidden: number; categoriesNoindex: number; brandPages: number; landings: number };
}

export function SeoReport() {
  const report = useQuery({ queryKey: ['seo-report'], queryFn: () => api.get<Report>('/seo/report') });
  if (report.isLoading) return <Loading text="Собираем отчёт…" />;
  if (!report.data) return <ErrorBox error={report.error} />;
  const r = report.data;
  return (
    <>
      <PageHeader title="Отчёт SEO" description="Дубли Title и H1 среди индексируемых страниц и сводка индексируемости (ADM-07)." />
      <div className="grid-3">
        <div className="stat"><strong>{r.indexing.indexable.toLocaleString('ru-RU')}</strong><span>карточек индексируется из {(r.indexing.products.published ?? 0).toLocaleString('ru-RU')} опубликованных</span></div>
        <div className="stat"><strong>{r.indexing.brandPages}</strong><span>страниц брендов</span></div>
        <div className="stat"><strong>{r.indexing.landings}</strong><span>SEO-посадочных</span></div>
        <div className="stat"><strong>{r.indexing.categoriesNoindex}</strong><span>разделов в noindex</span></div>
        <div className="stat"><strong>{r.indexing.pagesHidden}</strong><span>скрытых страниц</span></div>
      </div>
      <Panel title={`Дубли · ${r.duplicates.length}`}>
        {r.duplicates.length ? (
          <table className="table">
            <thead><tr><th>Поле</th><th>Язык</th><th>Значение</th><th>Страницы</th></tr></thead>
            <tbody>
              {r.duplicates.map((d, i) => (
                <tr key={i}><td>{d.field}</td><td>{d.lang}</td><td>{d.value}</td><td className="small">{d.pages.join(', ')}</td></tr>
              ))}
            </tbody>
          </table>
        ) : <Empty title="Дублей нет" />}
      </Panel>
    </>
  );
}
