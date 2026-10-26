/**
 * Карточка товара (ADM-03, ТЗ 5.2): поля по типу карточки, фасовки, документы, связи, разделы, SEO и история.
 * Поле, изменённое вручную, импорт больше не перезапишет (IMP-05); любую версию можно вернуть.
 */
import { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { ExternalLink, Plus, Trash2 } from 'lucide-react';
import { api, errorText } from '../api';
import { useAuth } from '../auth';
import { ShapeForm } from '../shape';
import type { HistoryEntry, Json, JsonObject } from '../types';
import { Badge, Button, Checkbox, ErrorBox, Field, formatDate, Loading, PageHeader, Panel, Select, Tabs, TextArea, TextInput, useToast } from '../ui';
import { STATUS } from './Products';

interface Packaging {
  id?: string;
  amount: string | null;
  unit: string | null;
  labelRu: string;
  labelEn: string;
  catalogNumber: string | null;
  availability: string;
}
interface Doc {
  id?: string;
  type: string;
  lang: string;
  titleRu: string | null;
  titleEn: string | null;
  href: string | null;
  access: string;
  rightsBasis: string | null;
}
type ProductData = JsonObject & {
  categories: { path: string; primary: boolean }[];
  packagings: Packaging[];
  documents: Doc[];
  relations: { relatedId: string; kind: string }[];
};
interface EditorData {
  id: string;
  data: ProductData;
  brand: { id: string; name: string; slug: string } | null;
  substance: { id: string; name: string } | null;
  related: Record<string, string>;
  completeness: number;
  indexable: boolean;
  source: string;
  controlled: string | null;
  manualFields: string[];
  url: string;
  demand: { views: number; requests: number };
  history: HistoryEntry[];
}

const TEXT_SHAPE: JsonObject = { description: [''], specs: [{ label: '', value: '' }], faq: [{ q: '', a: '' }], monograph: '' };
const DOC_TYPES = ['coa', 'sds', 'spec', 'datasheet', 'manual', 'certificate', 'strain-passport', 'leaflet', 'spectrum'];
const DOC_NAMES: Record<string, string> = { coa: 'Образец CoA', sds: 'SDS / MSDS', spec: 'Спецификация', datasheet: 'Datasheet', manual: 'Инструкция', certificate: 'Сертификат', 'strain-passport': 'Паспорт штамма', leaflet: 'Листок-вкладыш', spectrum: 'Спектр' };
type Tab = 'main' | 'chem' | 'storage' | 'texts' | 'packs' | 'docs' | 'links' | 'seo' | 'history';

export function ProductEditor() {
  const { id = '' } = useParams();
  const { can } = useAuth();
  const toast = useToast();
  const client = useQueryClient();
  const editor = useQuery({ queryKey: ['product', id], queryFn: () => api.get<EditorData>(`/products/${id}`) });
  const [data, setData] = useState<ProductData | null>(null);
  const [dirty, setDirty] = useState(false);
  const [tab, setTab] = useState<Tab>('main');
  const writable = can('products.write');

  useEffect(() => {
    if (editor.data && !dirty) setData(structuredClone(editor.data.data));
  }, [editor.data, dirty]);

  const saved = (r: EditorData, text: string) => {
    client.setQueryData(['product', id], r);
    setDirty(false);
    setData(structuredClone(r.data));
    toast(text);
  };
  const save = useMutation({
    mutationFn: () => api.put<EditorData>(`/products/${id}`, { data }),
    onSuccess: (r) => saved(r, 'Карточка сохранена — на сайте и в поиске через минуту'),
    onError: (e) => toast(errorText(e), 'bad'),
  });
  const restore = useMutation({
    mutationFn: (entry: number) => api.post<EditorData>(`/products/${id}/restore/${entry}`),
    onSuccess: (r) => saved(r, 'Карточка возвращена к выбранной версии'),
    onError: (e) => toast(errorText(e), 'bad'),
  });

  if (editor.isLoading || !data) return <Loading />;
  if (editor.error || !editor.data) return <ErrorBox error={editor.error} retry={() => void editor.refetch()} />;
  const e = editor.data;
  const set = (name: string, value: Json | unknown) => {
    setData({ ...data, [name]: value } as ProductData);
    setDirty(true);
  };
  const str = (name: string) => String(data[name] ?? '');
  const text = (name: string, label: string, hint?: string) => (
    <Field label={label} hint={hint}>
      <TextInput value={str(name)} disabled={!writable} onChange={(ev) => set(name, ev.target.value || null)} />
    </Field>
  );
  const manual = new Set(e.manualFields);

  return (
    <>
      <PageHeader
        title={`${e.brand?.name ?? ''} ${str('catalogNumber')}`}
        description={
          <>
            <Link to="/products">← Товары</Link> · {str('nameEn')} ·{' '}
            <a href={e.url} target="_blank" rel="noreferrer">
              на сайте <ExternalLink size={12} />
            </a>
          </>
        }
      />
      <div className="editor-actions">
        {writable ? (
          <Button variant="primary" busy={save.isPending} disabled={!dirty} onClick={() => save.mutate()}>
            Сохранить
          </Button>
        ) : null}
        <Badge tone={STATUS[str('status')]?.tone}>{STATUS[str('status')]?.label ?? str('status')}</Badge>
        <span className="muted">
          Полнота {e.completeness}/100 · {e.indexable ? 'индексируется' : 'не индексируется'} · источник {e.source} · просмотров {e.demand.views}, в заявках {e.demand.requests}
        </span>
        {e.controlled ? <Badge tone="bad">подконтрольное: {e.controlled}</Badge> : null}
        {dirty ? <span className="muted small">Есть несохранённые изменения</span> : null}
      </div>
      {e.manualFields.length ? <div className="note">Изменены вручную и защищены от импорта: {e.manualFields.join(', ')}</div> : null}
      <Tabs
        value={tab}
        onChange={setTab}
        items={[
          { key: 'main', label: 'Основное' }, { key: 'chem', label: 'Химия и техника' }, { key: 'storage', label: 'Хранение' },
          { key: 'texts', label: 'Тексты' }, { key: 'packs', label: `Фасовки · ${data.packagings.length}` },
          { key: 'docs', label: `Документы · ${data.documents.length}` }, { key: 'links', label: 'Разделы и связи' },
          { key: 'seo', label: 'SEO' }, { key: 'history', label: 'История' },
        ]}
      />
      {tab === 'main' ? (
        <Panel>
          <div className="form-grid">
            {text('nameEn', manual.has('name_en') ? 'Название EN (защищено от импорта)' : 'Название EN', 'По каталогу производителя (ТЗ 5.2)')}
            {text('nameRu', 'Название RU')}
            {text('slug', 'Адрес карточки', 'Смена адреса оставит 301 со старого (URL-03)')}
            <Field label="Статус">
              <Select value={str('status')} disabled={!writable} options={Object.entries(STATUS).map(([k, v]) => ({ value: k, label: v.label }))} onChange={(ev) => set('status', ev.target.value)} />
            </Field>
            <Field label="Тип карточки">
              <Select value={str('cardType')} disabled={!writable} options={[{ value: 'standard', label: 'Стандарты, примеси, реактивы' }, { value: 'equipment', label: 'Оборудование и колонки' }, { value: 'other', label: 'Прочее' }]} onChange={(ev) => set('cardType', ev.target.value)} />
            </Field>
            <Field label="Наличие">
              <Select value={str('availability')} disabled={!writable} options={[{ value: 'on_order', label: 'Под заказ' }, { value: 'in_stock', label: 'В наличии' }]} onChange={(ev) => set('availability', ev.target.value)} />
            </Field>
            <Field label="Индексация поисковиками (SEO-07)">
              <Select value={data.indexOverride === null || data.indexOverride === undefined ? '' : String(data.indexOverride)} disabled={!writable} options={[{ value: '', label: 'По полноте карточки' }, { value: 'true', label: 'Индексировать' }, { value: 'false', label: 'Не индексировать' }]} onChange={(ev) => set('indexOverride', ev.target.value === '' ? null : ev.target.value === 'true')} />
            </Field>
            <Field label="Своя фасовка (ТЗ 5.2.2)">
              <Select value={data.customPackaging === null || data.customPackaging === undefined ? '' : String(data.customPackaging)} disabled={!writable} options={[{ value: '', label: 'Как у бренда' }, { value: 'true', label: 'Любая фасовка под запрос' }, { value: 'false', label: 'Только фасовки производителя' }]} onChange={(ev) => set('customPackaging', ev.target.value === '' ? null : ev.target.value === 'true')} />
            </Field>
            <Checkbox label="Снят с производства (страница остаётся, «Подберите аналог»)" checked={!!data.discontinued} onChange={(v) => set('discontinued', v)} />
            <Checkbox label="Описание написано для этой карточки и проверено химиком" checked={!!data.uniqueDescription} onChange={(v) => set('uniqueDescription', v)} />
            {e.controlled ? (
              <Field label="Решение химика по перечням (ТЗ 5.2.1)">
                <Select value={str('controlledState')} disabled={!writable} options={[{ value: str('controlledState'), label: str('controlledState') || '—' }, { value: 'confirmed', label: 'Подконтрольное — скрыть' }, { value: 'cleared', label: 'Не подконтрольное' }]} onChange={(ev) => set('controlledState', ev.target.value)} />
              </Field>
            ) : null}
            <Field label="Синонимы (по строке)" wide>
              <TextArea value={((data.synonyms as string[]) ?? []).join('\n')} disabled={!writable} onChange={(ev) => set('synonyms', ev.target.value.split('\n').filter(Boolean))} />
            </Field>
          </div>
        </Panel>
      ) : null}
      {tab === 'chem' ? (
        <Panel>
          <div className="form-grid">
            {text('cas', 'CAS', 'Проверяется контрольная цифра')}
            <Field label="Альтернативные CAS (через запятую)">
              <TextInput value={((data.altCas as string[]) ?? []).join(', ')} disabled={!writable} onChange={(ev) => set('altCas', ev.target.value.split(',').map((x) => x.trim()).filter(Boolean))} />
            </Field>
            {text('formula', 'Брутто-формула')}
            {text('molecularWeight', 'Молекулярная масса')}
            {text('purity', 'Чистота')}
            {text('iupacName', 'Химическое название (IUPAC)')}
            <Field label="SMILES (для 2D-структуры)" wide>
              <TextInput value={str('smiles')} disabled={!writable} onChange={(ev) => set('smiles', ev.target.value || null)} />
            </Field>
            <Field label="Субстанция" hint={e.substance ? `Сейчас: ${e.substance.name}` : 'ID субстанции из раздела «Субстанции»'}>
              <TextInput value={str('substanceId')} disabled={!writable} onChange={(ev) => set('substanceId', ev.target.value || null)} />
            </Field>
            <Field label="Роль в субстанции">
              <Select value={str('substanceRole')} disabled={!writable} options={[{ value: '', label: '—' }, { value: 'api', label: 'Стандарт субстанции' }, { value: 'impurity', label: 'Примесь' }, { value: 'metabolite', label: 'Метаболит' }, { value: 'labeled', label: 'Меченое соединение' }]} onChange={(ev) => set('substanceRole', ev.target.value || null)} />
            </Field>
            <Field label="Атрибуты для фильтров (ключ: значения через запятую, по строке)" wide hint="phase: C18 · length: 150 mm · purpose: ВЭЖХ">
              <TextArea
                value={Object.entries((data.attributes as Record<string, string[]>) ?? {}).map(([k, v]) => `${k}: ${v.join(', ')}`).join('\n')}
                disabled={!writable}
                onChange={(ev) => set('attributes', Object.fromEntries(ev.target.value.split('\n').map((line) => line.split(':')).filter((p) => p.length > 1 && p[0].trim()).map(([k, ...rest]) => [k.trim(), rest.join(':').split(',').map((x) => x.trim()).filter(Boolean)])))}
              />
            </Field>
          </div>
        </Panel>
      ) : null}
      {tab === 'storage' ? (
        <Panel>
          <div className="form-grid">
            <Field label="Температура хранения">
              <Select value={str('storage')} disabled={!writable} options={[{ value: '', label: '—' }, { value: 'room', label: 'Комнатная' }, { value: '2-8', label: '+2…+8 °C' }, { value: '-20', label: '−20 °C' }, { value: '-80', label: '−80 °C' }]} onChange={(ev) => set('storage', ev.target.value || null)} />
            </Field>
            <Field label="Перевозка">
              <Select value={str('shipping')} disabled={!writable} options={[{ value: '', label: '—' }, { value: 'ambient', label: 'Обычные условия' }, { value: 'cold', label: 'Холодовая цепь' }, { value: 'dry-ice', label: 'Сухой лёд' }]} onChange={(ev) => set('shipping', ev.target.value || null)} />
            </Field>
            <Checkbox label="Опасный груз" checked={!!data.dangerousGoods} onChange={(v) => set('dangerousGoods', v)} />
          </div>
        </Panel>
      ) : null}
      {tab === 'texts' ? <Texts value={(data.texts as JsonObject) ?? {}} onChange={(v) => set('texts', v)} /> : null}
      {tab === 'packs' ? <Packagings rows={data.packagings} writable={writable} onChange={(rows) => set('packagings', rows)} /> : null}
      {tab === 'docs' ? <Documents rows={data.documents} writable={writable} onChange={(rows) => set('documents', rows)} /> : null}
      {tab === 'links' ? <Links data={data} related={e.related} writable={writable} set={set} /> : null}
      {tab === 'seo' ? (
        <Panel title="Title и Description вручную (SEO-02)">
          <p className="muted small">Пусто — шаблон из раздела «Шаблоны и robots.txt» или шаблон ТЗ 10.2.</p>
          {(['ru', 'en'] as const).map((lang) => {
            const seo = ((data.seo as Record<string, { title?: string; description?: string }>) ?? {})[lang] ?? {};
            const update = (field: 'title' | 'description', value: string) => set('seo', { ...((data.seo as JsonObject) ?? {}), [lang]: { ...seo, [field]: value } });
            return (
              <div key={lang} className="form-grid" style={{ marginBottom: 12 }}>
                <Field label={`Title ${lang.toUpperCase()}`} hint={`${(seo.title ?? '').length} символов`}>
                  <TextInput value={seo.title ?? ''} disabled={!writable} onChange={(ev) => update('title', ev.target.value)} />
                </Field>
                <Field label={`Description ${lang.toUpperCase()}`} hint={`${(seo.description ?? '').length} символов`}>
                  <TextArea value={seo.description ?? ''} disabled={!writable} onChange={(ev) => update('description', ev.target.value)} />
                </Field>
              </div>
            );
          })}
        </Panel>
      ) : null}
      {tab === 'history' ? (
        <Panel>
          <table className="table">
            <tbody>
              {e.history.map((h) => (
                <tr key={h.id}>
                  <td className="nowrap">{formatDate(h.at)}</td>
                  <td>{h.actor}</td>
                  <td className="muted">{h.summary}</td>
                  <td className="num">
                    {h.restorable && writable ? (
                      <Button size="sm" onClick={() => confirm('Вернуть карточку к этой версии?') && restore.mutate(h.id)}>
                        Вернуть
                      </Button>
                    ) : null}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {!e.history.length ? <p className="muted">Изменений в админке ещё не было.</p> : null}
        </Panel>
      ) : null}
    </>
  );
}

function Texts({ value, onChange }: { value: JsonObject; onChange: (v: JsonObject) => void }) {
  const [lang, setLang] = useState<'ru' | 'en'>('ru');
  return (
    <Panel>
      <Tabs value={lang} onChange={setLang} items={[{ key: 'ru', label: 'Русский' }, { key: 'en', label: 'English' }]} />
      <p className="muted small">Описание от 300 знаков, написанное для этой карточки, повышает полноту (ТЗ 5.6). Химические данные не придумываются — только из каталога производителя (ТЗ 10.4).</p>
      <ShapeForm value={(value[lang] as JsonObject) ?? {}} shape={TEXT_SHAPE} onChange={(v) => onChange({ ...value, [lang]: v })} />
    </Panel>
  );
}

function Packagings({ rows, writable, onChange }: { rows: Packaging[]; writable: boolean; onChange: (rows: Packaging[]) => void }) {
  const update = (i: number, patch: Partial<Packaging>) => onChange(rows.map((r, j) => (j === i ? { ...r, ...patch } : r)));
  return (
    <Panel title="Фасовки производителя" actions={writable ? <Button size="sm" onClick={() => onChange([...rows, { amount: '', unit: 'mg', labelRu: '', labelEn: '', catalogNumber: null, availability: 'on_order' }])}><Plus size={14} /> Фасовка</Button> : null}>
      <p className="muted small">Количество и единица — или подпись вроде «100 мг»: из неё фасовка разберётся сама. Подписи RU и EN, если пусты, составятся из количества.</p>
      <table className="table">
        <thead>
          <tr>
            <th>Кол-во</th>
            <th>Единица</th>
            <th>Подпись RU</th>
            <th>Подпись EN</th>
            <th>Свой кат. №</th>
            <th>Наличие</th>
            <th />
          </tr>
        </thead>
        <tbody>
          {rows.map((r, i) => (
            <tr key={r.id ?? `new-${i}`}>
              <td><TextInput value={r.amount ?? ''} disabled={!writable} onChange={(e) => update(i, { amount: e.target.value })} /></td>
              <td>
                <Select value={r.unit ?? ''} disabled={!writable} options={['', 'ug', 'mg', 'g', 'kg', 'ul', 'ml', 'l', 'pcs', 'pack', 'tests'].map((u) => ({ value: u, label: u || '—' }))} onChange={(e) => update(i, { unit: e.target.value || null })} />
              </td>
              <td><TextInput value={r.labelRu} disabled={!writable} onChange={(e) => update(i, { labelRu: e.target.value })} /></td>
              <td><TextInput value={r.labelEn} disabled={!writable} onChange={(e) => update(i, { labelEn: e.target.value })} /></td>
              <td><TextInput value={r.catalogNumber ?? ''} disabled={!writable} onChange={(e) => update(i, { catalogNumber: e.target.value || null })} /></td>
              <td>
                <Select value={r.availability} disabled={!writable} options={[{ value: 'on_order', label: 'Под заказ' }, { value: 'in_stock', label: 'В наличии' }]} onChange={(e) => update(i, { availability: e.target.value })} />
              </td>
              <td>{writable ? <button type="button" className="icon-btn" aria-label="Удалить" onClick={() => onChange(rows.filter((_, j) => j !== i))}><Trash2 size={15} /></button> : null}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </Panel>
  );
}

function Documents({ rows, writable, onChange }: { rows: Doc[]; writable: boolean; onChange: (rows: Doc[]) => void }) {
  const update = (i: number, patch: Partial<Doc>) => onChange(rows.map((r, j) => (j === i ? { ...r, ...patch } : r)));
  return (
    <Panel title="Документы" actions={writable ? <Button size="sm" onClick={() => onChange([...rows, { type: 'sds', lang: 'en', titleRu: null, titleEn: null, href: null, access: 'public', rightsBasis: null }])}><Plus size={14} /> Документ</Button> : null}>
      <p className="muted small">Файл производителя публикуется только с основанием права на публикацию (NFR-09). Без файла сайт покажет «Запросить»; CoA конкретной партии — всегда по запросу.</p>
      {rows.map((r, i) => (
        <div key={r.id ?? `new-${i}`} className="shape-item">
          <div className="form-grid">
            <Field label="Тип">
              <Select value={r.type} disabled={!writable} options={DOC_TYPES.map((t) => ({ value: t, label: DOC_NAMES[t] }))} onChange={(e) => update(i, { type: e.target.value })} />
            </Field>
            <Field label="Язык">
              <Select value={r.lang} disabled={!writable} options={[{ value: 'en', label: 'English' }, { value: 'ru', label: 'Русский' }]} onChange={(e) => update(i, { lang: e.target.value })} />
            </Field>
            <Field label="Доступ">
              <Select value={r.access} disabled={!writable} options={[{ value: 'public', label: 'Публично' }, { value: 'registered', label: 'После регистрации' }, { value: 'request', label: 'По запросу' }]} onChange={(e) => update(i, { access: e.target.value })} />
            </Field>
            <Field label="Название RU"><TextInput value={r.titleRu ?? ''} disabled={!writable} onChange={(e) => update(i, { titleRu: e.target.value || null })} /></Field>
            <Field label="Название EN"><TextInput value={r.titleEn ?? ''} disabled={!writable} onChange={(e) => update(i, { titleEn: e.target.value || null })} /></Field>
            <Field label="Файл (адрес)"><TextInput value={r.href ?? ''} disabled={!writable} onChange={(e) => update(i, { href: e.target.value || null })} /></Field>
            <Field label="Основание права на публикацию" wide>
              <TextInput value={r.rightsBasis ?? ''} disabled={!writable} placeholder="Например: медиакит производителя, письмо от 01.10.2026" onChange={(e) => update(i, { rightsBasis: e.target.value || null })} />
            </Field>
          </div>
          {writable ? (
            <div className="row row-end">
              <Button size="sm" variant="danger" onClick={() => onChange(rows.filter((_, j) => j !== i))}>Удалить документ</Button>
            </div>
          ) : null}
        </div>
      ))}
    </Panel>
  );
}

function Links({ data, related, writable, set }: { data: ProductData; related: Record<string, string>; writable: boolean; set: (name: string, value: unknown) => void }) {
  const [path, setPath] = useState('');
  const [relatedId, setRelatedId] = useState('');
  const [kind, setKind] = useState('analogue');
  const categories = data.categories;
  return (
    <div className="grid-2">
      <Panel title="Разделы каталога">
        <p className="muted small">Основной раздел даёт хлебные крошки (ТЗ 5.1); адрес карточки от раздела не зависит (URL-04).</p>
        <table className="table">
          <tbody>
            {categories.map((c) => (
              <tr key={c.path}>
                <td><code>{c.path}</code></td>
                <td>
                  <label className="checkbox">
                    <input type="radio" name="primary" checked={c.primary} disabled={!writable} onChange={() => set('categories', categories.map((x) => ({ ...x, primary: x.path === c.path })))} /> основной
                  </label>
                </td>
                <td className="num">{writable ? <button type="button" className="icon-btn" aria-label="Убрать" onClick={() => set('categories', categories.filter((x) => x.path !== c.path))}><Trash2 size={15} /></button> : null}</td>
              </tr>
            ))}
          </tbody>
        </table>
        {writable ? (
          <div className="row mt">
            <TextInput style={{ maxWidth: 300 }} placeholder="reference-standards/edqm" value={path} onChange={(e) => setPath(e.target.value)} />
            <Button size="sm" disabled={!path.trim()} onClick={() => { set('categories', [...categories, { path: path.trim().replace(/^\/|\/$/g, ''), primary: !categories.length }]); setPath(''); }}>
              Добавить раздел
            </Button>
          </div>
        ) : null}
      </Panel>
      <Panel title="Связанные товары">
        <p className="muted small">Аналоги с тем же CAS и примеси субстанции сайт находит сам; здесь — то, что задаётся вручную.</p>
        <table className="table">
          <tbody>
            {data.relations.map((r, i) => (
              <tr key={`${r.relatedId}-${r.kind}`}>
                <td>{{ analogue: 'Аналог', related: 'Связанный', accessory: 'Аксессуар' }[r.kind] ?? r.kind}</td>
                <td>{related[r.relatedId] ?? r.relatedId}</td>
                <td className="num">{writable ? <button type="button" className="icon-btn" aria-label="Убрать" onClick={() => set('relations', data.relations.filter((_, j) => j !== i))}><Trash2 size={15} /></button> : null}</td>
              </tr>
            ))}
          </tbody>
        </table>
        {writable ? (
          <div className="row mt">
            <Select style={{ maxWidth: 160 }} value={kind} options={[{ value: 'analogue', label: 'Аналог' }, { value: 'related', label: 'Связанный' }, { value: 'accessory', label: 'Аксессуар' }]} onChange={(e) => setKind(e.target.value)} />
            <TextInput style={{ maxWidth: 300 }} placeholder="ID товара (из адреса его карточки в админке)" value={relatedId} onChange={(e) => setRelatedId(e.target.value)} />
            <Button size="sm" disabled={!relatedId.trim()} onClick={() => { set('relations', [...data.relations, { relatedId: relatedId.trim(), kind }]); setRelatedId(''); }}>
              Добавить
            </Button>
          </div>
        ) : null}
      </Panel>
    </div>
  );
}
