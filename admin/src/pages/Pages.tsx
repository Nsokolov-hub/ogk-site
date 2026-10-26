import { useState } from 'react';
import { useNavigate } from 'react-router';
import { useMutation, useQuery } from '@tanstack/react-query';
import { Plus } from 'lucide-react';
import { api, errorText } from '../api';
import { useAuth } from '../auth';
import type { EditorView } from '../types';
import { Badge, Button, ErrorBox, Field, formatDate, Loading, Modal, PageHeader, Select, Tabs, TextInput, useToast } from '../ui';

interface PageRow {
  id: string;
  kind: string;
  slug: string;
  title: string;
  status: string;
  position: number;
  hasEn: boolean;
  hasDraft: boolean;
  publishAt: string | null;
  updatedAt: string | null;
  path: string;
}

/** Страницы сайта (ADM-02): главная, услуги, решения, статьи, авторы, страницы доверия */
export function Pages() {
  const { can } = useAuth();
  const navigate = useNavigate();
  const toast = useToast();
  const [kind, setKind] = useState('service');
  const [creating, setCreating] = useState(false);
  const [form, setForm] = useState({ kind: 'article', slug: '', title: '' });
  const list = useQuery({ queryKey: ['pages'], queryFn: () => api.get<{ items: PageRow[]; kinds: { key: string; name: string }[] }>('/pages') });
  const create = useMutation({
    mutationFn: () => api.post<EditorView>('/pages', form),
    onSuccess: (r) => navigate(`/edit/page/${r.id}`),
    onError: (e) => toast(errorText(e), 'bad'),
  });
  if (list.isLoading) return <Loading />;
  if (list.error || !list.data) return <ErrorBox error={list.error} retry={() => void list.refetch()} />;
  const rows = list.data.items.filter((p) => p.kind === kind);
  return (
    <>
      <PageHeader
        title="Страницы"
        description="Тексты сайта. Правки сохраняются черновиком: его видно по ссылке предпросмотра, на сайт он попадает после публикации."
        actions={
          can('pages.write') ? (
            <Button variant="primary" onClick={() => setCreating(true)}>
              <Plus size={15} /> Новая страница
            </Button>
          ) : null
        }
      />
      <Tabs value={kind} onChange={setKind} items={list.data.kinds.map((k) => ({ key: k.key, label: `${k.name} · ${list.data.items.filter((p) => p.kind === k.key).length}` }))} />
      <div className="panel table-wrap">
        <table className="table">
          <thead>
            <tr>
              <th>Заголовок</th>
              <th>Адрес</th>
              <th>Состояние</th>
              <th>EN</th>
              <th>Обновлена</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((p) => (
              <tr key={p.id} className="clickable" onClick={() => navigate(`/edit/page/${p.id}`)}>
                <td>{p.title}</td>
                <td>
                  <code>{p.path}</code>
                </td>
                <td className="nowrap">
                  {p.status === 'published' ? <Badge tone="good">опубликована</Badge> : <Badge>скрыта</Badge>}{' '}
                  {p.hasDraft ? <Badge tone="warn">черновик</Badge> : null} {p.publishAt ? <Badge tone="info">{formatDate(p.publishAt)}</Badge> : null}
                </td>
                <td>{p.hasEn ? <Badge tone="good">есть</Badge> : <span className="muted">—</span>}</td>
                <td className="nowrap muted">{formatDate(p.updatedAt, false)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {creating ? (
        <Modal title="Новая страница" onClose={() => setCreating(false)}>
          <div className="stack">
            <Field label="Вид">
              <Select value={form.kind} options={list.data.kinds.filter((k) => k.key !== 'home').map((k) => ({ value: k.key, label: k.name }))} onChange={(e) => setForm({ ...form, kind: e.target.value })} />
            </Field>
            <Field label="Заголовок (H1)">
              <TextInput value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} />
            </Field>
            <Field label="Адрес (латиница, через дефис)" hint="Например how-to-choose-hplc-column">
              <TextInput value={form.slug} onChange={(e) => setForm({ ...form, slug: e.target.value })} />
            </Field>
            <p className="muted small">Страница создаётся скрытой с полями своего вида; заполните их и опубликуйте.</p>
            <div className="row row-end">
              <Button variant="primary" busy={create.isPending} disabled={!form.title || !form.slug} onClick={() => create.mutate()}>
                Создать
              </Button>
            </div>
          </div>
        </Modal>
      ) : null}
    </>
  );
}
