/** Настройки сайта (ADM-09, ADM-10, ADM-11): контакты и реквизиты, счётчики, письма, полнота и индексация, фид. */
import { useEffect, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { api, errorText } from '../api';
import { useAuth } from '../auth';
import { ShapeForm } from '../shape';
import type { Json, JsonObject } from '../types';
import { Badge, Button, Checkbox, Field, formatDate, Loading, PageHeader, Panel, Tabs, TextArea, TextInput, useToast } from '../ui';

interface SettingsData {
  site: { ru: JsonObject; en: JsonObject };
  counters: { ym: number | null; ga: string | null };
  mail: Record<string, string>;
  index_threshold: number;
  completeness_weights: Record<string, number>;
  hide_controlled: boolean;
  feed: { categories: string[]; brands: string[] };
  integration: { crmUrl: string; deliveryEnabled: boolean; lastDeliveredAt: string | null; pending: number; brandsSyncedAt: string | null };
  server: { environment: string; siteUrl: string; salesEmail: string; alertEmails: string };
}

const WEIGHTS: Record<string, string> = { identity: 'Идентификаторы типа', image: 'Структура или фото', description: 'Описание от 300 знаков', document: 'Документ', link: 'Субстанция или раздел', storage: 'Условия хранения' };

export function Settings() {
  const { can } = useAuth();
  const toast = useToast();
  const client = useQueryClient();
  const data = useQuery({ queryKey: ['settings'], queryFn: () => api.get<SettingsData>('/settings') });
  const [local, setLocal] = useState<SettingsData | null>(null);
  const [lang, setLang] = useState<'ru' | 'en'>('ru');
  const feedCheck = useQuery({ queryKey: ['feed-check'], queryFn: () => api.get<{ items: number; categories: number; problems: string[]; url: string }>('/feed/check'), enabled: can('feeds.read') });
  useEffect(() => { if (data.data) setLocal(structuredClone(data.data)); }, [data.data]);
  const save = useMutation({
    mutationFn: ({ key, value }: { key: string; value: unknown }) => api.put<SettingsData>(`/settings/${key}`, { value }),
    onSuccess: (r, v) => {
      client.setQueryData(['settings'], r);
      toast(['index_threshold', 'completeness_weights', 'hide_controlled'].includes(v.key) ? 'Сохранено — каталог пересчитывается в фоне' : 'Сохранено');
      if (v.key === 'feed') void feedCheck.refetch();
    },
    onError: (e) => toast(errorText(e), 'bad'),
  });
  if (!local) return <Loading />;
  const admin = can('settings.write');
  const weightsSum = Object.values(local.completeness_weights).reduce((a, b) => a + b, 0);
  return (
    <>
      <PageHeader title="Настройки" description={`Окружение: ${local.server.environment} · ${local.server.siteUrl}`} />
      <Panel title="Контакты и реквизиты" actions={admin ? <Button size="sm" variant="primary" onClick={() => save.mutate({ key: 'site', value: local.site })}>Сохранить</Button> : null}>
        <p className="muted small">Один источник для шапки, подвала, страниц доверия и разметки Organization (ADM-10).</p>
        <Tabs value={lang} onChange={setLang} items={[{ key: 'ru', label: 'Русский' }, { key: 'en', label: 'English' }]} />
        <ShapeForm value={local.site[lang] as Json} shape={local.site.ru as Json} onChange={(v) => setLocal({ ...local, site: { ...local.site, [lang]: v as JsonObject } })} />
      </Panel>
      <div className="grid-2">
        <Panel title="Счётчики (ТЗ 15.1)" actions={admin ? <Button size="sm" variant="primary" onClick={() => save.mutate({ key: 'counters', value: local.counters })}>Сохранить</Button> : null}>
          <div className="stack">
            <Field label="Номер счётчика Яндекс Метрики" hint="Пусто — номер из настроек сервера (YM_COUNTER_ID)">
              <TextInput value={local.counters.ym ?? ''} onChange={(e) => setLocal({ ...local, counters: { ...local.counters, ym: e.target.value ? Number(e.target.value) : null } })} />
            </Field>
            <Field label="Идентификатор GA4" hint="G-XXXXXXX; пусто — из настроек сервера">
              <TextInput value={local.counters.ga ?? ''} onChange={(e) => setLocal({ ...local, counters: { ...local.counters, ga: e.target.value || null } })} />
            </Field>
            <p className="muted small">Счётчики загружаются только после согласия посетителя на аналитические cookies (NFR-06).</p>
          </div>
        </Panel>
        <Panel title="Письма (ADM-09)" actions={admin ? <Button size="sm" variant="primary" onClick={() => save.mutate({ key: 'mail', value: local.mail })}>Сохранить</Button> : null}>
          <div className="stack">
            <Field label="Отдел продаж (копии заявок)" hint={`Пусто — ${local.server.salesEmail}`}>
              <TextInput value={local.mail.sales_email ?? ''} onChange={(e) => setLocal({ ...local, mail: { ...local.mail, sales_email: e.target.value } })} />
            </Field>
            <Field label="Оповещения о недоставленных заявках" hint={`Через запятую; пусто — ${local.server.alertEmails}`}>
              <TextInput value={local.mail.alert_emails ?? ''} onChange={(e) => setLocal({ ...local, mail: { ...local.mail, alert_emails: e.target.value } })} />
            </Field>
            <Field label="Начало письма клиенту (RU)" hint="Пусто — стандартный текст; {number} — номер заявки">
              <TextArea value={local.mail.customer_intro_ru ?? ''} onChange={(e) => setLocal({ ...local, mail: { ...local.mail, customer_intro_ru: e.target.value } })} />
            </Field>
            <Field label="Начало письма клиенту (EN)">
              <TextArea value={local.mail.customer_intro_en ?? ''} onChange={(e) => setLocal({ ...local, mail: { ...local.mail, customer_intro_en: e.target.value } })} />
            </Field>
          </div>
        </Panel>
        <Panel title="Полнота и индексация (ТЗ 5.6, SEO-07)">
          <div className="stack">
            <Field label="Порог индексации" hint="Карточка с полнотой не ниже порога идёт в поисковики; старт — 70">
              <TextInput type="number" value={local.index_threshold} onChange={(e) => setLocal({ ...local, index_threshold: Number(e.target.value) })} />
            </Field>
            {admin ? <Button size="sm" onClick={() => save.mutate({ key: 'index_threshold', value: local.index_threshold })}>Сохранить порог</Button> : null}
            <div className="form-grid">
              {Object.entries(local.completeness_weights).map(([k, v]) => (
                <Field key={k} label={WEIGHTS[k] ?? k}>
                  <TextInput type="number" value={v} onChange={(e) => setLocal({ ...local, completeness_weights: { ...local.completeness_weights, [k]: Number(e.target.value) } })} />
                </Field>
              ))}
            </div>
            <p className={weightsSum === 100 ? 'muted small' : 'small'} style={weightsSum === 100 ? undefined : { color: 'var(--danger)' }}>Сумма весов: {weightsSum} (нужно 100)</p>
            {admin ? <Button size="sm" disabled={weightsSum !== 100} onClick={() => save.mutate({ key: 'completeness_weights', value: local.completeness_weights })}>Сохранить веса</Button> : null}
            <Checkbox label="Скрывать подконтрольные вещества с витрины, из поиска, Sitemap и фида (ТЗ 5.2.1)" checked={local.hide_controlled} onChange={(v) => { setLocal({ ...local, hide_controlled: v }); if (admin) save.mutate({ key: 'hide_controlled', value: v }); }} />
          </div>
        </Panel>
        <Panel title="YML-фид Директа (ADM-11)" actions={can('feeds.write') ? <Button size="sm" variant="primary" onClick={() => save.mutate({ key: 'feed', value: local.feed })}>Сохранить</Button> : null}>
          <div className="stack">
            <Field label="Разделы (по строке, путь раздела)">
              <TextArea value={local.feed.categories.join('\n')} onChange={(e) => setLocal({ ...local, feed: { ...local.feed, categories: e.target.value.split('\n').map((x) => x.trim()).filter(Boolean) } })} />
            </Field>
            <Field label="Бренды (по строке, адрес бренда; пусто — все)">
              <TextArea value={local.feed.brands.join('\n')} onChange={(e) => setLocal({ ...local, feed: { ...local.feed, brands: e.target.value.split('\n').map((x) => x.trim()).filter(Boolean) } })} />
            </Field>
            {feedCheck.data ? (
              <div className="small">
                <p>В фиде: {feedCheck.data.items.toLocaleString('ru-RU')} позиций, {feedCheck.data.categories} разделов · <a href={feedCheck.data.url} target="_blank" rel="noreferrer">открыть фид</a> (обновляется раз в 6 часов)</p>
                <ul>{feedCheck.data.problems.map((p) => <li key={p}>{p}</li>)}</ul>
              </div>
            ) : null}
          </div>
        </Panel>
        <Panel title="Связь с CRM">
          <p>Доставка заявок: {local.integration.deliveryEnabled ? <Badge tone="good">включена</Badge> : <Badge tone="warn">выключена</Badge>}</p>
          <p className="muted small">CRM: {local.integration.crmUrl || 'не задан'} · последняя доставка {formatDate(local.integration.lastDeliveredAt)} · в очереди {local.integration.pending}</p>
          <p className="muted small">Реестр производителей загружен: {formatDate(local.integration.brandsSyncedAt)}</p>
          <p className="muted small">Адрес CRM, токен и включение доставки задаются в настройках сервера (.env), чтобы секреты не хранились в базе.</p>
        </Panel>
      </div>
    </>
  );
}
