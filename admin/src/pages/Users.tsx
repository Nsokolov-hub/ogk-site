/** Сотрудники админки (ADM-01): роли, отключение доступа, сброс входа по коду. */
import { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Plus } from 'lucide-react';
import { api, errorText } from '../api';
import { Badge, Button, Checkbox, Field, formatDate, Loading, Modal, PageHeader, Select, TextInput, useToast } from '../ui';

interface User {
  id: string;
  email: string;
  name: string;
  role: string;
  roleName: string;
  active: boolean;
  totpEnabled: boolean;
  lastLoginAt: string | null;
}

const ROLE_HINTS: Record<string, string> = {
  admin: 'Всё, включая сотрудников, настройки, персональные данные заявок и подписчиков',
  content: 'Страницы, тексты разделов и брендов, SEO, редиректы',
  catalog: 'Товары, импорт, очереди, справочники, бренды и субстанции',
  viewer: 'Только просмотр, без персональных данных',
};

export function Users() {
  const toast = useToast();
  const client = useQueryClient();
  const [edit, setEdit] = useState<(Partial<User> & { password?: string }) | null>(null);
  const list = useQuery({ queryKey: ['users'], queryFn: () => api.get<{ items: User[]; roles: { key: string; name: string }[] }>('/users') });
  const done = () => {
    setEdit(null);
    void client.invalidateQueries({ queryKey: ['users'] });
  };
  const save = useMutation({
    mutationFn: () => (edit?.id ? api.patch(`/users/${edit.id}`, edit) : api.post('/users', edit)),
    onSuccess: () => { done(); toast('Сохранено'); },
    onError: (e) => toast(errorText(e), 'bad'),
  });
  const resetTotp = useMutation({
    mutationFn: (id: string) => api.post(`/users/${id}/reset-totp`),
    onSuccess: () => { done(); toast('Вход по коду сброшен: сотрудник включит его заново'); },
    onError: (e) => toast(errorText(e), 'bad'),
  });
  if (list.isLoading || !list.data) return <Loading />;
  return (
    <>
      <PageHeader title="Сотрудники" description="Учётные записи админки отделены от CRM и от посетителей сайта." actions={<Button variant="primary" onClick={() => setEdit({ role: 'content', active: true })}><Plus size={15} /> Сотрудник</Button>} />
      <div className="panel table-wrap">
        <table className="table">
          <thead><tr><th>Сотрудник</th><th>Роль</th><th>Вход по коду</th><th>Последний вход</th><th>Доступ</th></tr></thead>
          <tbody>
            {list.data.items.map((u) => (
              <tr key={u.id} className="clickable" onClick={() => setEdit(u)}>
                <td>{u.name}<div className="muted small">{u.email}</div></td>
                <td>{u.roleName}</td>
                <td>{u.totpEnabled ? <Badge tone="good">включён</Badge> : <Badge tone={u.role === 'admin' ? 'warn' : 'neutral'}>нет</Badge>}</td>
                <td className="muted nowrap">{formatDate(u.lastLoginAt)}</td>
                <td>{u.active ? <Badge tone="good">активен</Badge> : <Badge tone="bad">отключён</Badge>}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {edit ? (
        <Modal title={edit.id ? edit.name ?? 'Сотрудник' : 'Новый сотрудник'} onClose={() => setEdit(null)}>
          <div className="stack">
            <Field label="Имя"><TextInput value={edit.name ?? ''} onChange={(e) => setEdit({ ...edit, name: e.target.value })} /></Field>
            <Field label="Почта (логин)"><TextInput value={edit.email ?? ''} disabled={!!edit.id} onChange={(e) => setEdit({ ...edit, email: e.target.value })} /></Field>
            <Field label="Роль" hint={ROLE_HINTS[edit.role ?? 'content']}>
              <Select value={edit.role ?? 'content'} options={list.data.roles.map((r) => ({ value: r.key, label: r.name }))} onChange={(e) => setEdit({ ...edit, role: e.target.value })} />
            </Field>
            <Field label={edit.id ? 'Новый пароль (необязательно)' : 'Пароль'} hint="Не короче 12 символов; сотрудник сменит его в профиле">
              <TextInput type="password" autoComplete="new-password" value={edit.password ?? ''} onChange={(e) => setEdit({ ...edit, password: e.target.value })} />
            </Field>
            <Checkbox label="Доступ разрешён" checked={edit.active ?? true} onChange={(v) => setEdit({ ...edit, active: v })} />
            <div className="row row-end">
              {edit.id && edit.totpEnabled ? <Button variant="danger" onClick={() => confirm('Сбросить вход по коду? Сотрудник настроит его заново') && resetTotp.mutate(edit.id!)}>Сбросить вход по коду</Button> : null}
              <Button variant="primary" busy={save.isPending} onClick={() => save.mutate()}>Сохранить</Button>
            </div>
          </div>
        </Modal>
      ) : null}
    </>
  );
}
