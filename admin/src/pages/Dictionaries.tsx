/** Справочники (ADM-06): единицы, условия хранения, синонимы поиска, перечни подконтрольных веществ. */
import { useEffect, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Plus, Trash2 } from 'lucide-react';
import { api, errorText } from '../api';
import { useAuth } from '../auth';
import { Button, Empty, Loading, PageHeader, Pagination, Panel, TextArea, TextInput, useDebounced, useToast } from '../ui';

interface Entry {
  key: string;
  ru: string;
  en: string;
}
interface Dicts {
  units: Entry[];
  storage: Entry[];
  synonyms: string[][];
}

export function Dictionaries() {
  const { can } = useAuth();
  const toast = useToast();
  const client = useQueryClient();
  const writable = can('dictionaries.write');
  const data = useQuery({ queryKey: ['dictionaries'], queryFn: () => api.get<Dicts>('/dictionaries') });
  const save = useMutation({
    mutationFn: ({ name, value }: { name: string; value: unknown }) => api.put<Dicts>(`/dictionaries/${name}`, { value }),
    onSuccess: (r) => {
      client.setQueryData(['dictionaries'], r);
      toast('Справочник сохранён');
    },
    onError: (e) => toast(errorText(e), 'bad'),
  });
  if (data.isLoading || !data.data) return <Loading />;
  return (
    <>
      <PageHeader title="Справочники" description="Бренды и субстанции — в своих разделах; фильтры раздела — в редакторе раздела." />
      <div className="grid-2">
        <EntryList title="Единицы фасовок" rows={data.data.units} writable={writable} onSave={(value) => save.mutate({ name: 'units', value })} />
        <EntryList title="Условия хранения" rows={data.data.storage} writable={writable} onSave={(value) => save.mutate({ name: 'storage', value })} />
      </div>
      <Synonyms groups={data.data.synonyms} writable={writable} onSave={(value) => save.mutate({ name: 'synonyms', value })} />
      <Register writable={writable} />
    </>
  );
}

function EntryList({ title, rows, writable, onSave }: { title: string; rows: Entry[]; writable: boolean; onSave: (rows: Entry[]) => void }) {
  const [value, setValue] = useState(rows);
  useEffect(() => setValue(rows), [rows]);
  const update = (i: number, patch: Partial<Entry>) => setValue(value.map((r, j) => (j === i ? { ...r, ...patch } : r)));
  return (
    <Panel title={title} actions={writable ? <Button size="sm" variant="primary" onClick={() => onSave(value)}>Сохранить</Button> : null}>
      <table className="table">
        <thead><tr><th>Ключ</th><th>Русский</th><th>English</th><th /></tr></thead>
        <tbody>
          {value.map((r, i) => (
            <tr key={i}>
              <td><TextInput value={r.key} disabled={!writable} onChange={(e) => update(i, { key: e.target.value })} /></td>
              <td><TextInput value={r.ru} disabled={!writable} onChange={(e) => update(i, { ru: e.target.value })} /></td>
              <td><TextInput value={r.en} disabled={!writable} onChange={(e) => update(i, { en: e.target.value })} /></td>
              <td>{writable ? <button type="button" className="icon-btn" aria-label="Удалить" onClick={() => setValue(value.filter((_, j) => j !== i))}><Trash2 size={15} /></button> : null}</td>
            </tr>
          ))}
        </tbody>
      </table>
      {writable ? <Button size="sm" className="mt" onClick={() => setValue([...value, { key: '', ru: '', en: '' }])}><Plus size={14} /> Строка</Button> : null}
    </Panel>
  );
}

function Synonyms({ groups, writable, onSave }: { groups: string[][]; writable: boolean; onSave: (value: string[]) => void }) {
  const [text, setText] = useState(groups.map((g) => g.join(', ')).join('\n'));
  useEffect(() => setText(groups.map((g) => g.join(', ')).join('\n')), [groups]);
  return (
    <Panel title="Синонимы поиска (SRCH-05)" actions={writable ? <Button size="sm" variant="primary" onClick={() => onSave(text.split('\n').filter((l) => l.trim()))}>Сохранить</Button> : null}>
      <p className="muted small">Группа слов, которые поиск считает одинаковыми, — по строке через запятую: «ацетонитрил, acetonitrile, MeCN». Названия субстанций на двух языках уже работают как синонимы. Индекс обновится в течение минуты.</p>
      <TextArea rows={8} value={text} disabled={!writable} onChange={(e) => setText(e.target.value)} />
    </Panel>
  );
}

function Register({ writable }: { writable: boolean }) {
  const toast = useToast();
  const client = useQueryClient();
  const [q, setQ] = useState('');
  const [page, setPage] = useState(1);
  const search = useDebounced(q);
  const list = useQuery({ queryKey: ['register', search, page], queryFn: () => api.get<{ total: number; items: { id: string; list: string; name: string; cas: string[]; names: string[] }[] }>('/dictionaries/controlled', { q: search, page }) });
  const upload = useMutation({
    mutationFn: (file: File) => api.upload<{ entries: number; changed: number }>('/dictionaries/controlled', file),
    onSuccess: (r) => {
      toast(`Записей в перечнях: ${r.entries}; признак изменён у ${r.changed} товаров`);
      void client.invalidateQueries({ queryKey: ['register'] });
    },
    onError: (e) => toast(errorText(e), 'bad'),
  });
  return (
    <Panel title="Перечни подконтрольных веществ (ТЗ 5.2.1)">
      <p className="muted small">Файл xlsx с колонками «Перечень» (681 или 964), «Название», «CAS», «Синонимы» через «;». Загрузка заменяет перечни и перепроверяет весь каталог; решения химика не меняются.</p>
      <div className="row" style={{ marginBottom: 10 }}>
        <TextInput style={{ maxWidth: 300 }} placeholder="Поиск по названию" value={q} onChange={(e) => { setQ(e.target.value); setPage(1); }} />
        {writable ? <input type="file" accept=".xlsx" disabled={upload.isPending} onChange={(e) => { const f = e.target.files?.[0]; if (f && confirm('Заменить перечни этим файлом?')) upload.mutate(f); }} /> : null}
      </div>
      {list.isLoading ? <Loading /> : (
        <table className="table">
          <thead><tr><th>Перечень</th><th>Название</th><th>CAS</th><th>Синонимы</th></tr></thead>
          <tbody>
            {(list.data?.items ?? []).map((r) => (
              <tr key={r.id}><td>{r.list}</td><td>{r.name}</td><td>{r.cas.join(', ')}</td><td className="muted small">{r.names.slice(0, 5).join(', ')}</td></tr>
            ))}
          </tbody>
        </table>
      )}
      {list.data && !list.data.items.length ? <Empty title="Перечни не загружены" /> : null}
      <Pagination page={page} total={list.data?.total ?? 0} pageSize={100} onPage={setPage} />
    </Panel>
  );
}
