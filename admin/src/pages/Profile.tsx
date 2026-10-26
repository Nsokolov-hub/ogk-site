import { useEffect, useState } from 'react';
import QRCode from 'qrcode';
import { api, errorText } from '../api';
import { useAuth } from '../auth';
import type { Me } from '../types';
import { Badge, Button, Field, PageHeader, Panel, TextInput, useToast } from '../ui';

/** Профиль: пароль и вход по коду из приложения (TOTP, обязателен администраторам) */
export function Profile() {
  const { me, signedIn } = useAuth();
  const toast = useToast();
  const [setup, setSetup] = useState<{ secret: string; uri: string } | null>(null);
  const [qr, setQr] = useState('');
  const [code, setCode] = useState('');
  const [current, setCurrent] = useState('');
  const [password, setPassword] = useState('');
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (setup) QRCode.toDataURL(setup.uri, { margin: 1, width: 200 }).then(setQr).catch(() => setQr(''));
  }, [setup]);

  if (!me) return null;

  const startTotp = async () => {
    try {
      setSetup(await api.post('/auth/totp/setup'));
    } catch (e) {
      toast(errorText(e), 'bad');
    }
  };
  const confirmTotp = async () => {
    setBusy(true);
    try {
      signedIn(await api.post<Me>('/auth/totp/confirm', { code }));
      setSetup(null);
      toast('Вход по коду включён');
    } catch (e) {
      toast(errorText(e), 'bad');
    } finally {
      setBusy(false);
    }
  };
  const changePassword = async () => {
    setBusy(true);
    try {
      await api.post('/auth/password', { current, password });
      setCurrent('');
      setPassword('');
      toast('Пароль изменён, остальные сеансы закрыты');
    } catch (e) {
      toast(errorText(e), 'bad');
    } finally {
      setBusy(false);
    }
  };

  return (
    <>
      <PageHeader title="Профиль" description={`${me.name} · ${me.email} · ${me.roleName}`} />
      {me.totpSetupRequired ? (
        <div className="error-box">Администраторам нужен вход по коду из приложения: включите его, чтобы продолжить работу.</div>
      ) : null}
      <div className="grid-2">
        <Panel title="Вход по коду из приложения">
          <p>
            Состояние: {me.totpEnabled ? <Badge tone="good">включён</Badge> : <Badge tone="warn">выключен</Badge>}
          </p>
          {setup ? (
            <div className="stack">
              <p className="muted">Отсканируйте код в Яндекс Ключе, Google Authenticator или другом приложении и введите шесть цифр.</p>
              {qr ? <img src={qr} alt="QR-код для приложения" width={200} height={200} /> : null}
              <p className="muted small">
                Или введите ключ вручную: <code>{setup.secret}</code>
              </p>
              <Field label="Код из приложения">
                <TextInput inputMode="numeric" value={code} onChange={(e) => setCode(e.target.value)} />
              </Field>
              <Button variant="primary" busy={busy} onClick={confirmTotp}>
                Подтвердить
              </Button>
            </div>
          ) : (
            <Button variant={me.totpEnabled ? 'secondary' : 'primary'} onClick={startTotp}>
              {me.totpEnabled ? 'Перенастроить на новом телефоне' : 'Включить'}
            </Button>
          )}
        </Panel>
        <Panel title="Пароль">
          <div className="stack">
            <Field label="Текущий пароль">
              <TextInput type="password" autoComplete="current-password" value={current} onChange={(e) => setCurrent(e.target.value)} />
            </Field>
            <Field label="Новый пароль" hint="Не короче 12 символов">
              <TextInput type="password" autoComplete="new-password" value={password} onChange={(e) => setPassword(e.target.value)} />
            </Field>
            <Button busy={busy} disabled={!current || password.length < 12} onClick={changePassword}>
              Изменить пароль
            </Button>
          </div>
        </Panel>
      </div>
    </>
  );
}
