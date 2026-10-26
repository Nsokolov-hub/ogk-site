import { useState } from 'react';
import { api, ApiError, errorText } from '../api';
import { useAuth } from '../auth';
import type { Me } from '../types';
import { Button, Field, TextInput } from '../ui';

/** Вход сотрудника: почта и пароль, затем код из приложения, если вход по коду включён (ADM-01) */
export function Login() {
  const { signedIn } = useAuth();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [code, setCode] = useState('');
  const [needCode, setNeedCode] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      signedIn(await api.post<Me>('/auth/login', { email, password, code: code || undefined }));
    } catch (err) {
      if (err instanceof ApiError && err.code === 'TOTP_REQUIRED') setNeedCode(true);
      else setError(errorText(err));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="login">
      <form className="login-card" onSubmit={submit}>
        <img src="/favicon.svg" alt="" width={40} height={40} />
        <h1>Админка ОГК-ХИМ</h1>
        <p className="muted">Вход для сотрудников</p>
        <Field label="Почта">
          <TextInput type="email" autoComplete="username" required value={email} onChange={(e) => setEmail(e.target.value)} />
        </Field>
        <Field label="Пароль">
          <TextInput type="password" autoComplete="current-password" required value={password} onChange={(e) => setPassword(e.target.value)} />
        </Field>
        {needCode ? (
          <Field label="Код из приложения" hint="Шесть цифр из Яндекс Ключа, Google Authenticator или другого приложения">
            <TextInput inputMode="numeric" autoComplete="one-time-code" autoFocus value={code} onChange={(e) => setCode(e.target.value)} />
          </Field>
        ) : null}
        {error ? <div className="error-box">{error}</div> : null}
        <Button type="submit" variant="primary" busy={busy}>
          Войти
        </Button>
      </form>
    </div>
  );
}
