/**
 * Редактор текста страницы по форме его полей (ADM-02): строки — поля и абзацы, списки — повторяемые блоки,
 * вложенные объекты — группы. Форма полей (shape) приходит из API: из неё понятно, из чего состоит новый пункт
 * списка. Подписи полей — по-русски; служебные поля (дата обновления, признак перевода) скрыты.
 */
import { ArrowDown, ArrowUp, Plus, Trash2 } from 'lucide-react';
import type { Json, JsonObject } from './types';
import { Button, Checkbox, cn, Field, Select, TextArea, TextInput } from './ui';

const LABELS: Record<string, string> = {
  h1: 'H1', title: 'Title', description: 'Description', name: 'Название', summary: 'Кратко для списков', intro: 'Вступление',
  lead: 'Подзаголовок', text: 'Текст', seoText: 'Полезная информация (SEO-текст)', delivery: 'Условия поставки',
  faq: 'Вопросы и ответы', q: 'Вопрос', a: 'Ответ', documents: 'Документы', related: 'Внутренние ссылки', links: 'Ссылки',
  label: 'Подпись', href: 'Адрес ссылки', includes: 'Что входит', steps: 'Как работаем', needs: 'Что понадобится от клиента',
  table: 'Таблица', caption: 'Подпись таблицы', head: 'Заголовки столбцов', rows: 'Строки', countries: 'Страны',
  form: 'Форма расчёта', fields: 'Поля формы', image: 'Изображение', src: 'Файл (адрес)', alt: 'ALT', width: 'Ширина',
  height: 'Высота', tasks: 'Задачи', groups: 'Группы', scope: 'Разделы каталога (для счётчика)', featured: 'Разделы для «Часто заказывают»',
  services: 'Услуги', articles: 'Статьи', publishedAt: 'Дата публикации', authorSlug: 'Автор (адрес страницы автора)',
  reviewed: 'Проверено экспертом-химиком', readingMinutes: 'Минут на чтение', body: 'Текст статьи', cta: 'Призыв к действию',
  role: 'Роль', bio: 'Квалификация и опыт', photo: 'Фото', hero: 'Первый экран', slides: 'Слайды', subtitle: 'Подзаголовок',
  ctas: 'Кнопки', variant: 'Вид', icon: 'Иконка', imageMode: 'Как показывать картинку', search: 'Поиск', examples: 'Примеры запросов',
  facts: 'Факты', value: 'Значение', products: 'Блок товаров', accent: 'Акцент в заголовке', brands: 'Блок брендов', items: 'Пункты',
  logo: 'Логотип', promo: 'Промо-блок', quality: 'Блок качества', whyUs: 'Почему мы', textAccent: 'Акцент в тексте',
  capabilities: 'Возможности', prefix: 'Начало', suffix: 'Конец', request: 'Блок заявки', promises: 'Обещания', subscribe: 'Подписка',
  sections: 'Разделы', directions: 'Направления', audience: 'Для кого', supplyDocs: 'Сопроводительные документы', edo: 'ЭДО',
  licenses: 'Лицензии и сертификаты', captionLabel: 'Подпись', chips: 'Метки', id: 'Якорь (id)', synonyms: 'Синонимы',
  phone: 'Телефон', display: 'Как показывать', emails: 'Почта', info: 'Общая', order: 'Для заказов', address: 'Адрес',
  postalCode: 'Индекс', city: 'Город', street: 'Улица и дом', full: 'Полностью', mapQuery: 'Адрес для карты', hours: 'Часы работы',
  legal: 'Реквизиты', shortName: 'Краткое название', inn: 'ИНН', kpp: 'КПП', ogrn: 'ОГРН', docs: 'Документы (PDF)', consent: 'Согласие',
  privacy: 'Политика', card: 'Карточка организации', siteUrl: 'Адрес сайта', type: 'Тип блока', country: 'Страна', wave: 'Очередь',
  monograph: 'Фармакопейная статья', specs: 'Технические данные',
};

/** Поля, которые редактор не показывает: их ставит сам сайт */
const HIDDEN = new Set(['updatedAt', 'hasEn', 'facets', 'slug']);
/** Заголовки — во всю ширину, чтобы длинный H1 и Title были видны целиком */
const WIDE = new Set(['h1', 'title', 'name', 'href', 'src']);
const LONG = new Set(['description', 'intro', 'text', 'lead', 'a', 'summary', 'subtitle', 'bio', 'textAccent', 'edo', 'licenses']);
const OPTIONS: Record<string, string[]> = {
  variant: ['primary', 'secondary'],
  imageMode: ['cover', 'object'],
  icon: ['', 'plus', 'dot', 'arrow'],
  type: ['p', 'h2', 'ul', 'table', 'note'],
};
const BLOCK_NAMES: Record<string, string> = { p: 'Абзац', h2: 'Подзаголовок', ul: 'Список', table: 'Таблица', note: 'Примечание' };
const BLOCK_FIELDS: Record<string, string[]> = { p: ['text'], note: ['text'], h2: ['id', 'text'], ul: ['items'], table: ['caption', 'head', 'rows'] };

export const labelOf = (key: string) => LABELS[key] ?? key;

function isObject(value: unknown): value is JsonObject {
  return !!value && typeof value === 'object' && !Array.isArray(value);
}

/** Пустое значение по образцу: строки пустые, списки пустые, вложенное — так же */
export function blankLike(sample: Json | undefined): Json {
  if (Array.isArray(sample)) return [];
  if (isObject(sample)) return Object.fromEntries(Object.entries(sample).map(([k, v]) => [k, blankLike(v)]));
  if (typeof sample === 'boolean') return false;
  if (typeof sample === 'number') return sample;
  return '';
}

interface Props {
  value: Json;
  shape?: Json;
  onChange: (value: Json) => void;
  name?: string;
  depth?: number;
}

export function ShapeForm({ value, shape, onChange, name = '', depth = 0 }: Props) {
  if (isObject(value) || (value === null && isObject(shape))) {
    return <ObjectForm value={isObject(value) ? value : {}} shape={isObject(shape) ? shape : {}} onChange={onChange} depth={depth} />;
  }
  if (Array.isArray(value) || Array.isArray(shape)) {
    return <ListForm name={name} value={Array.isArray(value) ? value : []} shape={Array.isArray(shape) ? shape : []} onChange={onChange} depth={depth} />;
  }
  return <Scalar name={name} value={value} shape={shape} onChange={onChange} />;
}

function ObjectForm({ value, shape, onChange, depth }: { value: JsonObject; shape: JsonObject; onChange: (v: Json) => void; depth: number }) {
  const keys = [...new Set([...Object.keys(shape), ...Object.keys(value)])].filter((k) => !HIDDEN.has(k));
  const scalars = keys.filter((k) => !isObject(value[k] ?? shape[k]) && !Array.isArray(value[k] ?? shape[k]));
  const nested = keys.filter((k) => !scalars.includes(k));
  const set = (key: string, next: Json) => onChange({ ...value, [key]: next });
  return (
    <div className="shape-object">
      {scalars.length ? (
        <div className="form-grid">
          {scalars.map((key) => (
            <Scalar key={key} name={key} value={value[key] ?? null} shape={shape[key]} onChange={(v) => set(key, v)} />
          ))}
        </div>
      ) : null}
      {nested.map((key) => (
        <div key={key} className="shape-group">
          <div className="shape-head">
            <strong>{labelOf(key)}</strong>
          </div>
          <ShapeForm name={key} value={value[key] ?? (Array.isArray(shape[key]) ? [] : {})} shape={shape[key]} onChange={(v) => set(key, v)} depth={depth + 1} />
        </div>
      ))}
    </div>
  );
}

function ListForm({ name, value, shape, onChange, depth }: { name: string; value: Json[]; shape: Json[]; onChange: (v: Json) => void; depth: number }) {
  const sample = shape[0] ?? value[0];
  const objects = isObject(sample);
  const lists = Array.isArray(sample);
  const blocks = name === 'body';
  const move = (from: number, to: number) => {
    if (to < 0 || to >= value.length) return;
    const next = [...value];
    const [item] = next.splice(from, 1);
    next.splice(to, 0, item);
    onChange(next);
  };
  const remove = (i: number) => onChange(value.filter((_, j) => j !== i));
  const update = (i: number, item: Json) => onChange(value.map((v, j) => (j === i ? item : v)));
  const add = (item: Json) => onChange([...value, item]);

  if (!objects && !lists) {
    // Список строк: абзацы, пункты, страны, разделы
    const long = name === 'text' || name === 'seoText' || name === 'delivery' || name === 'bio';
    return (
      <div>
        {value.map((item, i) => (
          <div key={i} className="shape-list-row">
            {long ? (
              <TextArea value={String(item ?? '')} rows={3} onChange={(e) => update(i, e.target.value)} />
            ) : (
              <TextInput value={String(item ?? '')} onChange={(e) => update(i, e.target.value)} />
            )}
            <ItemTools onUp={() => move(i, i - 1)} onDown={() => move(i, i + 1)} onRemove={() => remove(i)} />
          </div>
        ))}
        <Button size="sm" className="mt" onClick={() => add('')}>
          <Plus size={14} /> Добавить
        </Button>
      </div>
    );
  }
  return (
    <div>
      {value.map((item, i) => (
        <div key={i} className="shape-item">
          <div className="shape-item-tools">
            <span className="muted small grow">{blocks && isObject(item) ? BLOCK_NAMES[String(item.type)] ?? String(item.type) : `№ ${i + 1}`}</span>
            <ItemTools onUp={() => move(i, i - 1)} onDown={() => move(i, i + 1)} onRemove={() => remove(i)} />
          </div>
          {blocks && isObject(item) ? (
            <BlockForm value={item} onChange={(v) => update(i, v)} />
          ) : (
            <ShapeForm name={name} value={item} shape={sample} onChange={(v) => update(i, v)} depth={depth + 1} />
          )}
        </div>
      ))}
      {blocks ? (
        <div className="row mt">
          {Object.entries(BLOCK_NAMES).map(([type, label]) => (
            <Button key={type} size="sm" onClick={() => add(type === 'ul' ? { type, items: [''] } : type === 'table' ? { type, caption: '', head: ['', ''], rows: [['', '']] } : type === 'h2' ? { type, id: '', text: '' } : { type, text: '' })}>
              <Plus size={14} /> {label}
            </Button>
          ))}
        </div>
      ) : (
        <Button size="sm" className="mt" onClick={() => add(lists ? [] : blankLike(sample))}>
          <Plus size={14} /> Добавить
        </Button>
      )}
    </div>
  );
}

function BlockForm({ value, onChange }: { value: JsonObject; onChange: (v: Json) => void }) {
  const type = String(value.type ?? 'p');
  const fields = BLOCK_FIELDS[type] ?? ['text'];
  const shapes: Record<string, Json> = { text: '', id: '', caption: '', items: [''], head: [''], rows: [['']] };
  return (
    <div className="stack">
      {fields.map((field) => (
        <div key={field}>
          {['items', 'head', 'rows'].includes(field) ? <div className="field-label">{labelOf(field)}</div> : null}
          <ShapeForm
            name={field}
            value={value[field] ?? shapes[field]}
            shape={shapes[field]}
            onChange={(v) => onChange({ ...value, [field]: v })}
          />
        </div>
      ))}
    </div>
  );
}

function ItemTools({ onUp, onDown, onRemove }: { onUp: () => void; onDown: () => void; onRemove: () => void }) {
  return (
    <span className="row" style={{ gap: 0, flexWrap: 'nowrap' }}>
      <button type="button" className="icon-btn" aria-label="Выше" onClick={onUp}>
        <ArrowUp size={15} />
      </button>
      <button type="button" className="icon-btn" aria-label="Ниже" onClick={onDown}>
        <ArrowDown size={15} />
      </button>
      <button type="button" className="icon-btn" aria-label="Удалить" onClick={onRemove}>
        <Trash2 size={15} />
      </button>
    </span>
  );
}

function Scalar({ name, value, shape, onChange }: { name: string; value: Json; shape?: Json; onChange: (v: Json) => void }) {
  const label = labelOf(name);
  const sample = value ?? shape;
  if (typeof sample === 'boolean') return <Checkbox label={label} checked={!!value} onChange={onChange} />;
  if (typeof sample === 'number') {
    return (
      <Field label={label}>
        <TextInput type="number" value={value === null ? '' : String(value)} onChange={(e) => onChange(e.target.value === '' ? null : Number(e.target.value))} />
      </Field>
    );
  }
  if (OPTIONS[name]) {
    return (
      <Field label={label}>
        <Select value={String(value ?? '')} options={OPTIONS[name].map((o) => ({ value: o, label: o === '' ? '—' : BLOCK_NAMES[o] ?? o }))} onChange={(e) => onChange(e.target.value)} />
      </Field>
    );
  }
  const text = value === null || value === undefined ? '' : String(value);
  const long = LONG.has(name) || text.length > 90;
  return (
    <Field label={label} wide={long || WIDE.has(name)} hint={name === 'title' ? `${text.length} символов, лучше до 70` : name === 'description' ? `${text.length} символов, лучше 120–160` : undefined}>
      {long ? <TextArea className={cn('input', 'textarea')} value={text} rows={name === 'text' || name === 'a' ? 4 : 2} onChange={(e) => onChange(e.target.value)} /> : <TextInput value={text} onChange={(e) => onChange(e.target.value)} />}
    </Field>
  );
}
