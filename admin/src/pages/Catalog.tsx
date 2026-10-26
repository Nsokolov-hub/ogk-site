/** Разделы каталога, бренды и субстанции (ADM-02, ADM-06): списки и создание; тексты — в редакторе страниц. */
import { useState } from 'react';
import { useNavigate } from 'react-router';
import { useMutation, useQuery } from '@tanstack/react-query';
import { Plus } from 'lucide-react';
import { api, errorText } from '../api';
import { useAuth } from '../auth';
import type { EditorView } from '../types';
import { Badge, Button, Empty, ErrorBox, Field, Loading, Modal, PageHeader, Pagination, Select, TextInput, useDebounced, useToast } from '../ui';

interface CategoryRow {
  id: string;
  path: string;
  parentId: string | null;
  nameRu: string;
  nameEn: string | null;
  facets: string[];
  isIndexed: boolean;
  hasEn: boolean;
  hasDraft: boolean;
  count: number;
}

export function Categories() {
  const { can } = useAuth();
  const navigate = useNavigate();
  const toast = useToast();
  const [form, setForm] = useState<{ parentPath: string; slug: string; nameRu: string } | null>(null);
  const list = useQuery({ queryKey: ['categories'], queryFn: () => api.get<{ items: CategoryRow[] }>('/categories') });
  const create = useMutation({
    mutationFn: () => api.post<EditorView>('/categories', { ...form, parentPath: form?.parentPath || null }),
    onSuccess: (r) => navigate(`/edit/category/${r.id}`),
    onError: (e) => toast(errorText(e), 'bad'),
  });
  if (list.isLoading) return <Loading />;
  if (list.error || !list.data) return <ErrorBox error={list.error} />;
  const roots = list.data.items.filter((c) => !c.parentId);
  return (
    <>
      <PageHeader
        title="Разделы каталога"
        description="Дерево каталога (ТЗ 4.2): тексты, фильтры и индексация раздела. Число — позиции, для которых раздел основной."
        actions={can('taxonomy.write') ? <Button variant="primary" onClick={() => setForm({ parentPath: '', slug: '', nameRu: '' })}><Plus size={15} /> Подраздел</Button> : null}
      />
      <div className="panel table-wrap">
        <table className="table">
          <thead>
            <tr>
              <th>Раздел</th>
              <th>Адрес</th>
              <th>Фильтры</th>
              <th>Состояние</th>
              <th className="num">Позиций</th>
            </tr>
          </thead>
          <tbody>
            {roots.flatMap((root) => [root, ...list.data.items.filter((c) => c.parentId === root.id)]).map((c) => (
              <tr key={c.id} className="clickable" onClick={() => navigate(`/edit/category/${c.id}`)}>
                <td style={{ paddingLeft: c.parentId ? 32 : 10 }}>{c.nameRu}</td>
                <td>
                  <code>/catalog/{c.path}/</code>
                </td>
                <td className="muted small">{c.facets.join(', ')}</td>
                <td className="nowrap">
                  {c.isIndexed ? null : <Badge tone="warn">noindex</Badge>} {c.hasEn ? <Badge tone="good">EN</Badge> : null} {c.hasDraft ? <Badge tone="warn">черновик</Badge> : null}
                </td>
                <td className="num">{c.count.toLocaleString('ru-RU')}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {form ? (
        <Modal title="Новый подраздел" onClose={() => setForm(null)}>
          <div className="stack">
            <Field label="Родительский раздел">
              <Select value={form.parentPath} options={[{ value: '', label: '— верхний уровень —' }, ...roots.map((r) => ({ value: r.path, label: r.nameRu }))]} onChange={(e) => setForm({ ...form, parentPath: e.target.value })} />
            </Field>
            <Field label="Название">
              <TextInput value={form.nameRu} onChange={(e) => setForm({ ...form, nameRu: e.target.value })} />
            </Field>
            <Field label="Адрес (латиница)">
              <TextInput value={form.slug} onChange={(e) => setForm({ ...form, slug: e.target.value })} />
            </Field>
            <div className="row row-end">
              <Button variant="primary" busy={create.isPending} disabled={!form.nameRu || !form.slug} onClick={() => create.mutate()}>
                Создать
              </Button>
            </div>
          </div>
        </Modal>
      ) : null}
    </>
  );
}

interface BrandRow {
  id: string;
  slug: string;
  name: string;
  pagePublished: boolean;
  customPackaging: boolean;
  crmLinked: boolean;
  count: number;
  hasDraft: boolean;
  hasEn: boolean;
}

export function Brands() {
  const { can } = useAuth();
  const navigate = useNavigate();
  const toast = useToast();
  const [q, setQ] = useState('');
  const [published, setPublished] = useState('');
  const [page, setPage] = useState(1);
  const [name, setName] = useState<string | null>(null);
  const search = useDebounced(q);
  const list = useQuery({
    queryKey: ['brands', search, published, page],
    queryFn: () => api.get<{ total: number; items: BrandRow[] }>('/brands', { q: search, published: published || undefined, page }),
  });
  const create = useMutation({
    mutationFn: () => api.post<EditorView>('/brands', { name }),
    onSuccess: (r) => navigate(`/edit/brand/${r.id}`),
    onError: (e) => toast(errorText(e), 'bad'),
  });
  return (
    <>
      <PageHeader
        title="Бренды"
        description="Производители каталога. Реестр сверяется с CRM (поток F5); написания помогают импорту узнавать бренд."
        actions={can('taxonomy.write') ? <Button variant="primary" onClick={() => setName('')}><Plus size={15} /> Бренд</Button> : null}
      />
      <div className="filters">
        <TextInput placeholder="Название или адрес" value={q} onChange={(e) => { setQ(e.target.value); setPage(1); }} />
        <Select value={published} options={[{ value: '', label: 'Все бренды' }, { value: 'true', label: 'Со страницей на сайте' }, { value: 'false', label: 'Без страницы' }]} onChange={(e) => { setPublished(e.target.value); setPage(1); }} />
      </div>
      <ErrorBox error={list.error} />
      {list.isLoading ? <Loading /> : (
        <div className="panel table-wrap">
          <table className="table">
            <thead>
              <tr>
                <th>Бренд</th>
                <th>Страница</th>
                <th>CRM</th>
                <th>Фасовка</th>
                <th className="num">Товаров</th>
              </tr>
            </thead>
            <tbody>
              {(list.data?.items ?? []).map((b) => (
                <tr key={b.id} className="clickable" onClick={() => navigate(`/edit/brand/${b.id}`)}>
                  <td>
                    {b.name} {b.hasDraft ? <Badge tone="warn">черновик</Badge> : null}
                  </td>
                  <td>{b.pagePublished ? <Badge tone="good">/brands/{b.slug}/</Badge> : <span className="muted">—</span>}</td>
                  <td>{b.crmLinked ? <Badge tone="info">в реестре</Badge> : <span className="muted">—</span>}</td>
                  <td>{b.customPackaging ? 'под запрос' : <span className="muted">фиксированная</span>}</td>
                  <td className="num">{b.count.toLocaleString('ru-RU')}</td>
                </tr>
              ))}
            </tbody>
          </table>
          {list.data && !list.data.items.length ? <Empty title="Ничего не найдено" /> : null}
          <Pagination page={page} total={list.data?.total ?? 0} pageSize={50} onPage={setPage} />
        </div>
      )}
      {name !== null ? (
        <Modal title="Новый бренд" onClose={() => setName(null)}>
          <div className="stack">
            <Field label="Название" hint="Адрес страницы составится из названия">
              <TextInput value={name} onChange={(e) => setName(e.target.value)} />
            </Field>
            <div className="row row-end">
              <Button variant="primary" busy={create.isPending} disabled={!name.trim()} onClick={() => create.mutate()}>
                Создать
              </Button>
            </div>
          </div>
        </Modal>
      ) : null}
    </>
  );
}

interface SubstanceRow {
  id: string;
  slug: string;
  nameRu: string;
  nameEn: string;
  cas: string | null;
  synonyms: string[];
  count: number;
  hasDraft: boolean;
}

export function Substances() {
  const { can } = useAuth();
  const navigate = useNavigate();
  const toast = useToast();
  const [q, setQ] = useState('');
  const [form, setForm] = useState<{ nameRu: string; nameEn: string; cas: string } | null>(null);
  const search = useDebounced(q);
  const list = useQuery({ queryKey: ['substances', search], queryFn: () => api.get<{ items: SubstanceRow[] }>('/substances', { q: search }) });
  const create = useMutation({
    mutationFn: () => api.post<EditorView>('/substances', { ...form, cas: form?.cas || null }),
    onSuccess: (r) => navigate(`/edit/substance/${r.id}`),
    onError: (e) => toast(errorText(e), 'bad'),
  });
  return (
    <>
      <PageHeader
        title="Субстанции"
        description="МНН — родитель стандартов и примесей (SC-05). Синонимы и названия на двух языках работают в поиске сайта (SRCH-05)."
        actions={can('taxonomy.write') ? <Button variant="primary" onClick={() => setForm({ nameRu: '', nameEn: '', cas: '' })}><Plus size={15} /> Субстанция</Button> : null}
      />
      <div className="filters">
        <TextInput placeholder="МНН или CAS" value={q} onChange={(e) => setQ(e.target.value)} />
      </div>
      {list.isLoading ? <Loading /> : (
        <div className="panel table-wrap">
          <table className="table">
            <thead>
              <tr>
                <th>МНН</th>
                <th>English</th>
                <th>CAS</th>
                <th>Синонимы</th>
                <th className="num">Позиций</th>
              </tr>
            </thead>
            <tbody>
              {(list.data?.items ?? []).map((s) => (
                <tr key={s.id} className="clickable" onClick={() => navigate(`/edit/substance/${s.id}`)}>
                  <td>
                    {s.nameRu} {s.hasDraft ? <Badge tone="warn">черновик</Badge> : null}
                  </td>
                  <td>{s.nameEn}</td>
                  <td className="nowrap">{s.cas ?? '—'}</td>
                  <td className="muted small">{s.synonyms.slice(0, 4).join(', ')}</td>
                  <td className="num">{s.count}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      {form ? (
        <Modal title="Новая субстанция" onClose={() => setForm(null)}>
          <div className="stack">
            <Field label="МНН на русском">
              <TextInput value={form.nameRu} onChange={(e) => setForm({ ...form, nameRu: e.target.value })} />
            </Field>
            <Field label="МНН на английском" hint="Из него составится адрес страницы">
              <TextInput value={form.nameEn} onChange={(e) => setForm({ ...form, nameEn: e.target.value })} />
            </Field>
            <Field label="CAS">
              <TextInput value={form.cas} onChange={(e) => setForm({ ...form, cas: e.target.value })} />
            </Field>
            <div className="row row-end">
              <Button variant="primary" busy={create.isPending} disabled={!form.nameRu || !form.nameEn} onClick={() => create.mutate()}>
                Создать
              </Button>
            </div>
          </div>
        </Modal>
      ) : null}
    </>
  );
}
