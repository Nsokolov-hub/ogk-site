/** Товары (ADM-03): фильтры по бренду, разделу, статусу, полноте, источнику и индексации; массовые действия. */
import { useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Plus } from 'lucide-react';
import { api, errorText } from '../api';
import { useAuth } from '../auth';
import { Badge, Button, Checkbox, Empty, ErrorBox, Field, formatDate, Loading, Modal, PageHeader, Pagination, Select, TextInput, useDebounced, useToast } from '../ui';

interface Row {
  id: string;
  slug: string;
  catalogNumber: string;
  name: string;
  cas: string | null;
  brand: string;
  category: string | null;
  status: string;
  completeness: number;
  indexable: boolean;
  source: string;
  controlled: string | null;
  availability: string;
  updatedAt: string;
}

export const STATUS: Record<string, { label: string; tone: 'good' | 'warn' | 'neutral' | 'bad' }> = {
  published: { label: 'опубликован', tone: 'good' },
  moderation: { label: 'на модерации', tone: 'warn' },
  draft: { label: 'черновик', tone: 'neutral' },
  archived: { label: 'архив', tone: 'bad' },
};

const BULK = [
  { value: '', label: 'Действие с выбранными…' },
  { value: 'status:published', label: 'Опубликовать' },
  { value: 'status:moderation', label: 'На модерацию' },
  { value: 'status:archived', label: 'В архив' },
  { value: 'availability:in_stock', label: 'Наличие: в наличии' },
  { value: 'availability:on_order', label: 'Наличие: под заказ' },
  { value: 'index_override:true', label: 'Индексировать вручную' },
  { value: 'index_override:false', label: 'Не индексировать' },
  { value: 'index_override:null', label: 'Индексация по полноте' },
  { value: 'primary_category', label: 'Основной раздел…' },
  { value: 'add_category', label: 'Добавить раздел…' },
  { value: 'reindex', label: 'Переиндексировать' },
];

export function Products() {
  const { can } = useAuth();
  const navigate = useNavigate();
  const toast = useToast();
  const client = useQueryClient();
  const [params, setParams] = useSearchParams();
  const [selected, setSelected] = useState<string[]>([]);
  const [bulk, setBulk] = useState('');
  const [creating, setCreating] = useState(false);
  const [q, setQ] = useState(params.get('q') ?? '');
  const search = useDebounced(q);
  const filters = {
    q: search,
    brand: params.get('brand') ?? '',
    category: params.get('category') ?? '',
    status: params.get('status') ?? '',
    source: params.get('source') ?? '',
    indexable: params.get('indexable') ?? '',
    controlled: params.get('controlled') ?? '',
    no_category: params.get('no_category') ?? '',
    min_completeness: params.get('min_completeness') ?? '',
    max_completeness: params.get('max_completeness') ?? '',
    sort: params.get('sort') ?? 'updated',
    page: Number(params.get('page') ?? 1),
  };
  const list = useQuery({ queryKey: ['products', filters], queryFn: () => api.get<{ total: number; items: Row[]; pageSize: number }>('/products', filters) });
  const set = (key: string, value: string) => {
    const next = new URLSearchParams(params);
    if (value) next.set(key, value);
    else next.delete(key);
    if (key !== 'page') next.delete('page');
    setParams(next);
    setSelected([]);
  };
  const run = useMutation({
    mutationFn: async () => {
      let [action, raw] = bulk.split(':');
      let value: unknown = raw === 'true' ? true : raw === 'false' ? false : raw === 'null' ? null : raw;
      if (action === 'primary_category' || action === 'add_category') {
        const path = prompt('Путь раздела, например chromatography/hplc-columns');
        if (!path) throw new Error('Раздел не указан');
        value = path.trim().replace(/^\/?(catalog\/)?|\/$/g, '');
      }
      action = action ?? '';
      return api.post<{ updated: number }>('/products/bulk', { ids: selected, action, value });
    },
    onSuccess: (r) => {
      toast(`Изменено товаров: ${r.updated}`);
      setSelected([]);
      setBulk('');
      void client.invalidateQueries({ queryKey: ['products'] });
    },
    onError: (e) => toast(errorText(e), 'bad'),
  });
  const items = list.data?.items ?? [];
  const allSelected = items.length > 0 && items.every((i) => selected.includes(i.id));

  return (
    <>
      <PageHeader
        title="Товары"
        description="Опубликованный товар виден на сайте и в поиске по сайту; в поисковики он попадает при полноте не ниже порога (SEO-07)."
        actions={can('products.write') ? <Button variant="primary" onClick={() => setCreating(true)}><Plus size={15} /> Товар</Button> : null}
      />
      <div className="filters">
        <TextInput placeholder="Кат. №, CAS или название" value={q} onChange={(e) => { setQ(e.target.value); set('page', ''); }} />
        <TextInput placeholder="Бренд (адрес, например edqm)" defaultValue={filters.brand} onBlur={(e) => set('brand', e.target.value.trim())} />
        <TextInput placeholder="Раздел (например reagents)" defaultValue={filters.category} onBlur={(e) => set('category', e.target.value.trim())} />
        <Select value={filters.status} onChange={(e) => set('status', e.target.value)} options={[{ value: '', label: 'Любой статус' }, ...Object.entries(STATUS).map(([k, v]) => ({ value: k, label: v.label }))]} />
        <Select value={filters.indexable} onChange={(e) => set('indexable', e.target.value)} options={[{ value: '', label: 'Индексация: любая' }, { value: 'true', label: 'Индексируется' }, { value: 'false', label: 'Не индексируется' }]} />
        <Select value={filters.source} onChange={(e) => set('source', e.target.value)} options={[{ value: '', label: 'Любой источник' }, { value: 'import:', label: 'Импорт' }, { value: 'manual', label: 'Вручную' }, { value: 'seed', label: 'Тестовый каталог' }, { value: 'crm', label: 'Из CRM' }]} />
        <Select value={filters.controlled} onChange={(e) => set('controlled', e.target.value)} options={[{ value: '', label: 'Подконтрольные: все' }, { value: 'yes', label: 'Подконтрольные' }, { value: 'review', label: 'Спорные' }, { value: 'no', label: 'Обычные' }]} />
        <TextInput type="number" placeholder="Полнота от" defaultValue={filters.min_completeness} onBlur={(e) => set('min_completeness', e.target.value)} />
        <TextInput type="number" placeholder="Полнота до" defaultValue={filters.max_completeness} onBlur={(e) => set('max_completeness', e.target.value)} />
        <Select value={filters.sort} onChange={(e) => set('sort', e.target.value)} options={[{ value: 'updated', label: 'Сначала изменённые' }, { value: 'completeness', label: 'По полноте' }, { value: 'popularity', label: 'По популярности' }, { value: 'name', label: 'По названию' }]} />
        <Checkbox label="Без раздела" checked={filters.no_category === 'true'} onChange={(v) => set('no_category', v ? 'true' : '')} />
      </div>
      {can('products.write') ? (
        <div className="row" style={{ marginBottom: 10 }}>
          <Select style={{ maxWidth: 280 }} value={bulk} options={BULK} onChange={(e) => setBulk(e.target.value)} />
          <Button disabled={!bulk || !selected.length} busy={run.isPending} onClick={() => confirm(`Применить к ${selected.length} товарам?`) && run.mutate()}>
            Применить к выбранным ({selected.length})
          </Button>
        </div>
      ) : null}
      <ErrorBox error={list.error} retry={() => void list.refetch()} />
      {list.isLoading ? <Loading /> : (
        <div className="panel table-wrap">
          <table className="table">
            <thead>
              <tr>
                <th>
                  <input type="checkbox" aria-label="Выбрать все на странице" checked={allSelected} onChange={(e) => setSelected(e.target.checked ? items.map((i) => i.id) : [])} />
                </th>
                <th>Кат. №</th>
                <th>Название</th>
                <th>Бренд</th>
                <th>Раздел</th>
                <th>Статус</th>
                <th className="num">Полнота</th>
                <th>Изменён</th>
              </tr>
            </thead>
            <tbody>
              {items.map((p) => (
                <tr key={p.id} className="clickable" onClick={() => navigate(`/products/${p.id}`)}>
                  <td onClick={(e) => e.stopPropagation()}>
                    <input type="checkbox" aria-label={`Выбрать ${p.catalogNumber}`} checked={selected.includes(p.id)} onChange={(e) => setSelected(e.target.checked ? [...selected, p.id] : selected.filter((x) => x !== p.id))} />
                  </td>
                  <td className="nowrap">{p.catalogNumber}</td>
                  <td>
                    {p.name}
                    {p.cas ? <div className="muted small">CAS {p.cas}</div> : null}
                  </td>
                  <td>{p.brand}</td>
                  <td className="muted small">{p.category ?? <Badge tone="warn">нет</Badge>}</td>
                  <td className="nowrap">
                    <Badge tone={STATUS[p.status]?.tone}>{STATUS[p.status]?.label ?? p.status}</Badge> {p.controlled ? <Badge tone="bad">{p.controlled}</Badge> : null}
                  </td>
                  <td className="num">
                    {p.completeness} {p.indexable ? <Badge tone="good">index</Badge> : null}
                  </td>
                  <td className="nowrap muted">{formatDate(p.updatedAt, false)}</td>
                </tr>
              ))}
            </tbody>
          </table>
          {!items.length ? <Empty title="Товаров не найдено">Измените фильтры.</Empty> : null}
          <Pagination page={filters.page} total={list.data?.total ?? 0} pageSize={list.data?.pageSize ?? 50} onPage={(p) => set('page', String(p))} />
        </div>
      )}
      {creating ? <NewProduct onClose={() => setCreating(false)} /> : null}
    </>
  );
}

function NewProduct({ onClose }: { onClose: () => void }) {
  const navigate = useNavigate();
  const toast = useToast();
  const [brandQuery, setBrandQuery] = useState('');
  const [form, setForm] = useState({ brandId: '', catalogNumber: '', nameEn: '', cardType: 'standard', categoryPath: '' });
  const search = useDebounced(brandQuery);
  const brands = useQuery({ queryKey: ['brands-pick', search], queryFn: () => api.get<{ items: { id: string; name: string }[] }>('/brands', { q: search }), enabled: search.length > 1 });
  const create = useMutation({
    mutationFn: () => api.post<{ id: string }>('/products', { ...form, categoryPath: form.categoryPath || null }),
    onSuccess: (r) => navigate(`/products/${r.id}`),
    onError: (e) => toast(errorText(e), 'bad'),
  });
  return (
    <Modal title="Новый товар" onClose={onClose}>
      <div className="stack">
        <Field label="Бренд" hint="Начните вводить название">
          <TextInput value={brandQuery} onChange={(e) => setBrandQuery(e.target.value)} />
        </Field>
        {brands.data?.items.length ? (
          <Select value={form.brandId} options={[{ value: '', label: 'Выберите бренд' }, ...brands.data.items.map((b) => ({ value: b.id, label: b.name }))]} onChange={(e) => setForm({ ...form, brandId: e.target.value })} />
        ) : null}
        <Field label="Каталожный номер">
          <TextInput value={form.catalogNumber} onChange={(e) => setForm({ ...form, catalogNumber: e.target.value })} />
        </Field>
        <Field label="Название EN (по каталогу производителя)">
          <TextInput value={form.nameEn} onChange={(e) => setForm({ ...form, nameEn: e.target.value })} />
        </Field>
        <Field label="Тип карточки">
          <Select value={form.cardType} options={[{ value: 'standard', label: 'Стандарты, примеси, реактивы' }, { value: 'equipment', label: 'Оборудование и колонки' }, { value: 'other', label: 'Прочее' }]} onChange={(e) => setForm({ ...form, cardType: e.target.value })} />
        </Field>
        <Field label="Основной раздел" hint="Например reference-standards/edqm">
          <TextInput value={form.categoryPath} onChange={(e) => setForm({ ...form, categoryPath: e.target.value })} />
        </Field>
        <div className="row row-end">
          <Button variant="primary" busy={create.isPending} disabled={!form.brandId || !form.catalogNumber || !form.nameEn} onClick={() => create.mutate()}>
            Создать черновик
          </Button>
        </div>
      </div>
    </Modal>
  );
}
