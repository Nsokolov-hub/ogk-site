/**
 * Редактор страницы, раздела, бренда, субстанции или SEO-посадочной (ADM-02): черновик → предпросмотр на сайте →
 * публикация сейчас или в выбранное время; версии из журнала возвращаются черновиком.
 */
import { useEffect, useMemo, useState } from 'react';
import { Link, useParams } from 'react-router';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { ExternalLink, Plus, Trash2 } from 'lucide-react';
import { api, errorText } from '../api';
import { useAuth } from '../auth';
import { ShapeForm } from '../shape';
import type { EditorView, Json, JsonObject } from '../types';
import { Badge, Button, Checkbox, ErrorBox, Field, formatDate, Loading, PageHeader, Panel, Select, Tabs, TextArea, TextInput, useToast } from '../ui';

const FACETS: { key: string; label: string }[] = [
  { key: 'brand', label: 'Производитель' }, { key: 'pack', label: 'Фасовка' }, { key: 'storage', label: 'Хранение' },
  { key: 'purpose', label: 'Назначение' }, { key: 'type', label: 'Тип продукции' }, { key: 'phase', label: 'Фаза' },
  { key: 'length', label: 'Длина' }, { key: 'diameter', label: 'Диаметр' }, { key: 'particle', label: 'Размер частиц' },
  { key: 'ph', label: 'pH' },
];
const RIGHTS: Record<string, string> = { page: 'pages.write', category: 'taxonomy.write', brand: 'taxonomy.write', substance: 'taxonomy.write', landing: 'seo.write' };
const BACK: Record<string, [string, string]> = {
  page: ['/pages', 'Страницы'], category: ['/categories', 'Разделы'], brand: ['/brands', 'Бренды'],
  substance: ['/substances', 'Субстанции'], landing: ['/landings', 'SEO-посадочные'],
};
const ACTIONS: Record<string, string> = {
  publish: 'опубликовано', publish_scheduled: 'опубликовано по расписанию', schedule: 'запланировано', create: 'создано',
  restore: 'возвращена версия', publish_failed: 'публикация не удалась', alias_added: 'добавлено написание', alias_removed: 'удалено написание',
};

type Data = JsonObject & { content?: { ru?: JsonObject; en?: JsonObject } };

export function EntityEditor() {
  const { entity = 'page', id = '' } = useParams();
  const { can } = useAuth();
  const toast = useToast();
  const client = useQueryClient();
  const key = ['edit', entity, id];
  const view = useQuery({ queryKey: key, queryFn: () => api.get<EditorView>(`/edit/${entity}/${id}`) });
  const [data, setData] = useState<Data | null>(null);
  const [lang, setLang] = useState<'ru' | 'en'>('ru');
  const [dirty, setDirty] = useState(false);
  const [at, setAt] = useState('');
  const writable = can(RIGHTS[entity] ?? 'pages.write');

  useEffect(() => {
    if (view.data && !dirty) setData(structuredClone((view.data.draft ?? view.data.published) as Data));
  }, [view.data, dirty]);

  const done = (result: EditorView, text: string) => {
    client.setQueryData(key, result);
    setDirty(false);
    setData(structuredClone((result.draft ?? result.published) as Data));
    toast(text);
  };
  const save = useMutation({
    mutationFn: () => api.put<EditorView>(`/edit/${entity}/${id}/draft`, { data }),
    onSuccess: (r) => done(r, 'Черновик сохранён — его видно по ссылке предпросмотра'),
    onError: (e) => toast(errorText(e), 'bad'),
  });
  const publish = useMutation({
    mutationFn: async (when?: string) => {
      if (dirty) await api.put(`/edit/${entity}/${id}/draft`, { data });
      return api.post<EditorView>(`/edit/${entity}/${id}/publish`, when ? { at: new Date(when).toISOString() } : {});
    },
    onSuccess: (r, when) => done(r, when ? 'Публикация запланирована' : 'Опубликовано — сайт обновится через несколько секунд'),
    onError: (e) => toast(errorText(e), 'bad'),
  });
  const discard = useMutation({
    mutationFn: () => api.delete<EditorView>(`/edit/${entity}/${id}/draft`),
    onSuccess: (r) => done(r, 'Черновик удалён'),
    onError: (e) => toast(errorText(e), 'bad'),
  });
  const restore = useMutation({
    mutationFn: (entry: number) => api.post<EditorView>(`/edit/${entity}/${id}/restore/${entry}`),
    onSuccess: (r) => done(r, 'Версия стала черновиком: проверьте и опубликуйте'),
    onError: (e) => toast(errorText(e), 'bad'),
  });

  const content = (data?.content ?? {}) as { ru?: JsonObject; en?: JsonObject };
  const meta = useMemo(() => {
    if (!data) return null;
    const rest = { ...data };
    delete rest.content;
    return rest;
  }, [data]);

  if (view.isLoading || !data || !meta) return <Loading />;
  if (view.error) return <ErrorBox error={view.error} retry={() => void view.refetch()} />;
  const v = view.data!;
  const change = (next: Data) => {
    setData(next);
    setDirty(true);
  };
  const setMeta = (name: string, value: Json) => change({ ...data, [name]: value });
  const setContent = (which: 'ru' | 'en', value: Json) => change({ ...data, content: { ...content, [which]: value as JsonObject } });
  const [backTo, backLabel] = BACK[entity] ?? ['/', 'Сводка'];

  return (
    <>
      <PageHeader
        title={`${v.title}: ${v.label}`}
        description={
          <>
            <Link to={backTo}>← {backLabel}</Link> · адрес на сайте <code>{v.path}</code>
            {v.draft ? <> · <Badge tone="warn">черновик{v.draftAuthor ? ` (${v.draftAuthor}, ${formatDate(v.draftUpdatedAt)})` : ''}</Badge></> : null}
            {v.publishAt ? <> · <Badge tone="info">публикация {formatDate(v.publishAt)}</Badge></> : null}
          </>
        }
      />
      {writable ? (
        <div className="editor-actions">
          <Button variant="primary" busy={save.isPending} disabled={!dirty} onClick={() => save.mutate()}>
            Сохранить черновик
          </Button>
          <Button busy={publish.isPending} onClick={() => confirm('Опубликовать изменения на сайте?') && publish.mutate(undefined)}>
            Опубликовать
          </Button>
          <TextInput type="datetime-local" style={{ width: 210 }} value={at} onChange={(e) => setAt(e.target.value)} aria-label="Время публикации" />
          <Button disabled={!at} onClick={() => publish.mutate(at)}>
            Запланировать
          </Button>
          <a className="btn btn-ghost" href={v.previewUrl} target="_blank" rel="noreferrer" title="Черновик на сайте: сохраните его перед просмотром">
            <ExternalLink size={15} /> Предпросмотр
          </a>
          {content.en ? (
            <a className="btn btn-ghost" href={v.previewUrlEn} target="_blank" rel="noreferrer">
              <ExternalLink size={15} /> EN
            </a>
          ) : null}
          {v.draft ? (
            <Button variant="danger" onClick={() => confirm('Удалить черновик? Опубликованная версия останется') && discard.mutate()}>
              Удалить черновик
            </Button>
          ) : null}
          {dirty ? <span className="muted small">Есть несохранённые изменения</span> : null}
        </div>
      ) : (
        <div className="note">Только просмотр: у вашей роли нет права менять эту страницу.</div>
      )}

      <Panel title="Основное">
        <MetaForm entity={entity} kind={v.kind} meta={meta} onChange={setMeta} />
      </Panel>
      {entity === 'brand' ? <Aliases brandId={id} writable={writable} /> : null}

      <Panel title="Текст страницы">
        <Tabs
          value={lang}
          onChange={setLang}
          items={[
            { key: 'ru', label: 'Русская версия' },
            { key: 'en', label: content.en ? 'English' : 'English — нет перевода' },
          ]}
        />
        {lang === 'ru' ? (
          <ShapeForm value={content.ru ?? {}} shape={v.shape} onChange={(value) => setContent('ru', value)} />
        ) : content.en ? (
          <>
            <div className="row row-end">
              <Button size="sm" variant="danger" onClick={() => confirm('Убрать английскую версию? /en/-страница закроется от индексации') && change({ ...data, content: { ru: content.ru ?? {} } })}>
                Убрать перевод
              </Button>
            </div>
            <ShapeForm value={content.en} shape={v.shape} onChange={(value) => setContent('en', value)} />
          </>
        ) : (
          <div className="empty">
            <strong>Английской версии нет</strong>
            <p className="muted">Без перевода /en/-страница закрыта от индексации и не попадает в Sitemap (EN-05).</p>
            <Button className="mt" onClick={() => setContent('en', structuredClone(content.ru ?? {}))}>
              <Plus size={14} /> Начать перевод с копии русского текста
            </Button>
          </div>
        )}
      </Panel>

      <Panel title="История">
        {v.history.length ? (
          <table className="table">
            <tbody>
              {v.history.map((h) => (
                <tr key={h.id}>
                  <td className="nowrap">{formatDate(h.at)}</td>
                  <td>{h.actor}</td>
                  <td>{ACTIONS[h.action] ?? h.action}</td>
                  <td className="muted">{h.summary}</td>
                  <td className="num">
                    {h.restorable && writable ? (
                      <Button size="sm" onClick={() => restore.mutate(h.id)}>
                        Вернуть эту версию
                      </Button>
                    ) : null}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : (
          <p className="muted">Изменений ещё не было.</p>
        )}
      </Panel>
    </>
  );
}

function MetaForm({ entity, kind, meta, onChange }: { entity: string; kind: string | null; meta: JsonObject; onChange: (name: string, value: Json) => void }) {
  const text = (name: string, label: string, hint?: string) => (
    <Field label={label} hint={hint}>
      <TextInput value={String(meta[name] ?? '')} onChange={(e) => onChange(name, e.target.value)} />
    </Field>
  );
  const number = (name: string, label: string, hint?: string) => (
    <Field label={label} hint={hint}>
      <TextInput type="number" value={meta[name] === null || meta[name] === undefined ? '' : String(meta[name])} onChange={(e) => onChange(name, e.target.value === '' ? null : Number(e.target.value))} />
    </Field>
  );
  const status = () => (
    <Field label="Статус">
      <Select value={String(meta.status ?? 'published')} options={[{ value: 'published', label: 'Опубликована' }, { value: 'hidden', label: 'Скрыта' }]} onChange={(e) => onChange('status', e.target.value)} />
    </Field>
  );
  const facets = () => {
    const selected = (meta.facets as string[] | undefined) ?? [];
    return (
      <Field label="Фильтры раздела (ТЗ 5.5)" wide>
        <div className="row">
          {FACETS.map((f) => (
            <Checkbox key={f.key} label={f.label} checked={selected.includes(f.key)} onChange={(on) => onChange('facets', on ? [...selected, f.key] : selected.filter((x) => x !== f.key))} />
          ))}
        </div>
      </Field>
    );
  };

  if (entity === 'page') {
    return (
      <div className="form-grid">
        {kind !== 'home' ? text('slug', 'Адрес (slug)', 'Смена адреса оставит 301 со старого') : null}
        {number('position', 'Порядок в списке')}
        {kind !== 'home' ? status() : null}
      </div>
    );
  }
  if (entity === 'category') {
    return (
      <div className="form-grid">
        {text('nameRu', 'Название')}
        {text('nameEn', 'Название EN')}
        {text('shortRu', 'Короткое название (меню)')}
        {text('shortEn', 'Короткое название EN')}
        {number('position', 'Порядок')}
        <Field label="Тип карточки по умолчанию">
          <Select value={String(meta.cardType ?? 'standard')} options={[{ value: 'standard', label: 'Стандарты и реактивы' }, { value: 'equipment', label: 'Оборудование и колонки' }, { value: 'other', label: 'Прочее' }]} onChange={(e) => onChange('cardType', e.target.value)} />
        </Field>
        <Checkbox label="Индексируется поисковиками" checked={!!meta.isIndexed} onChange={(v) => onChange('isIndexed', v)} />
        {facets()}
      </div>
    );
  }
  if (entity === 'brand') {
    return (
      <div className="form-grid">
        {text('name', 'Название')}
        {text('country', 'Страна')}
        {text('logo', 'Логотип (адрес файла)')}
        {number('position', 'Порядок в списках')}
        <Field label="Очередь (ТЗ 4.2)">
          <Select value={String(meta.wave ?? '')} options={[{ value: '', label: '—' }, { value: '1', label: 'Первая' }, { value: '2', label: 'Вторая' }]} onChange={(e) => onChange('wave', e.target.value ? Number(e.target.value) : null)} />
        </Field>
        <Checkbox label="Страница бренда опубликована" checked={!!meta.pagePublished} onChange={(v) => onChange('pagePublished', v)} />
        <Checkbox label="Любая фасовка под запрос (ТЗ 5.2.2)" checked={!!meta.customPackaging} onChange={(v) => onChange('customPackaging', v)} />
        <Checkbox label="Официальный партнёр" checked={!!meta.isPartner} onChange={(v) => onChange('isPartner', v)} />
      </div>
    );
  }
  if (entity === 'substance') {
    return (
      <div className="form-grid">
        {text('nameRu', 'МНН на русском')}
        {text('nameEn', 'МНН на английском')}
        {text('cas', 'CAS')}
        {text('formula', 'Брутто-формула')}
        {text('molecularWeight', 'Молекулярная масса')}
        <Field label="Синонимы (по строке; ищутся на сайте)" wide>
          <TextArea value={((meta.synonyms as string[]) ?? []).join('\n')} onChange={(e) => onChange('synonyms', e.target.value.split('\n'))} />
        </Field>
      </div>
    );
  }
  // SEO-посадочная
  const filters = (meta.filters as Record<string, string[]>) ?? {};
  return (
    <div className="form-grid">
      {text('categoryPath', 'Раздел каталога', 'Например chromatography/hplc-columns')}
      {text('slug', 'Адрес среза (slug)')}
      {number('position', 'Порядок')}
      {status()}
      <Field label="Фиксированные фильтры среза" wide hint="Ключ фильтра и значения через запятую, как в адресе каталога: brand = waters; phase = C18">
        <div className="stack">
          {Object.entries(filters).map(([facet, values]) => (
            <div key={facet} className="shape-list-row">
              <Select style={{ maxWidth: 200 }} value={facet} options={FACETS.map((f) => ({ value: f.key, label: f.label }))} onChange={(e) => {
                const next = { ...filters };
                delete next[facet];
                onChange('filters', { ...next, [e.target.value]: values });
              }} />
              <TextInput value={values.join(', ')} onChange={(e) => onChange('filters', { ...filters, [facet]: e.target.value.split(',').map((x) => x.trim()).filter(Boolean) })} />
              <button type="button" className="icon-btn" aria-label="Убрать фильтр" onClick={() => {
                const next = { ...filters };
                delete next[facet];
                onChange('filters', next);
              }}>
                <Trash2 size={15} />
              </button>
            </div>
          ))}
          <div>
            <Button size="sm" onClick={() => onChange('filters', { ...filters, [FACETS.find((f) => !(f.key in filters))?.key ?? 'brand']: [] })}>
              <Plus size={14} /> Фильтр
            </Button>
          </div>
        </div>
      </Field>
    </div>
  );
}

function Aliases({ brandId, writable }: { brandId: string; writable: boolean }) {
  const toast = useToast();
  const client = useQueryClient();
  const [name, setName] = useState('');
  const list = useQuery({ queryKey: ['aliases', brandId], queryFn: () => api.get<{ id: string; name: string; source: string }[]>(`/brands/${brandId}/aliases`) });
  const add = useMutation({
    mutationFn: () => api.post<{ id: string; name: string; source: string }[]>(`/brands/${brandId}/aliases`, { name }),
    onSuccess: (r) => {
      client.setQueryData(['aliases', brandId], r);
      setName('');
    },
    onError: (e) => toast(errorText(e), 'bad'),
  });
  const remove = useMutation({
    mutationFn: (aliasId: string) => api.delete<{ id: string; name: string; source: string }[]>(`/brands/${brandId}/aliases/${aliasId}`),
    onSuccess: (r) => client.setQueryData(['aliases', brandId], r),
  });
  return (
    <Panel title="Написания бренда" actions={<span className="muted small">По ним импорт узнаёт производителя в прайсах (IMP-03)</span>}>
      <div className="row">
        {(list.data ?? []).map((a) => (
          <span key={a.id} className="badge">
            {a.name} <span className="muted">· {a.source}</span>
            {writable ? (
              <button type="button" className="icon-btn" aria-label={`Удалить ${a.name}`} onClick={() => remove.mutate(a.id)}>
                <Trash2 size={13} />
              </button>
            ) : null}
          </span>
        ))}
      </div>
      {writable ? (
        <div className="row mt">
          <TextInput style={{ maxWidth: 320 }} placeholder="Ещё одно написание" value={name} onChange={(e) => setName(e.target.value)} />
          <Button size="sm" disabled={!name.trim()} busy={add.isPending} onClick={() => add.mutate()}>
            Добавить
          </Button>
        </div>
      ) : null}
    </Panel>
  );
}
