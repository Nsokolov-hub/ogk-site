/** Общие элементы интерфейса админки: кнопки, поля, таблицы, вкладки, окна, уведомления. */
import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from 'react';
import { X } from 'lucide-react';
import { errorText } from './api';

export function cn(...parts: (string | false | null | undefined)[]) {
  return parts.filter(Boolean).join(' ');
}

export function Button({
  children,
  variant = 'secondary',
  size,
  busy,
  className,
  ...rest
}: React.ButtonHTMLAttributes<HTMLButtonElement> & { variant?: 'primary' | 'secondary' | 'danger' | 'ghost'; size?: 'sm'; busy?: boolean }) {
  return (
    <button type="button" className={cn('btn', `btn-${variant}`, size === 'sm' && 'btn-sm', className)} disabled={busy || rest.disabled} {...rest}>
      {busy ? <span className="spinner" aria-hidden /> : null}
      {children}
    </button>
  );
}

export function Field({ label, hint, error, children, wide }: { label: string; hint?: string; error?: string | null; children: ReactNode; wide?: boolean }) {
  return (
    <label className={cn('field', wide && 'field-wide')}>
      <span className="field-label">{label}</span>
      {children}
      {hint ? <span className="field-hint">{hint}</span> : null}
      {error ? <span className="field-error">{error}</span> : null}
    </label>
  );
}

export function TextInput(props: React.InputHTMLAttributes<HTMLInputElement>) {
  return <input className="input" {...props} />;
}

export function TextArea(props: React.TextareaHTMLAttributes<HTMLTextAreaElement>) {
  return <textarea className="input textarea" rows={props.rows ?? 3} {...props} />;
}

export function Select({ options, ...props }: React.SelectHTMLAttributes<HTMLSelectElement> & { options: { value: string; label: string }[] }) {
  return (
    <select className="input" {...props}>
      {options.map((o) => (
        <option key={o.value} value={o.value}>
          {o.label}
        </option>
      ))}
    </select>
  );
}

export function Checkbox({ label, checked, onChange }: { label: string; checked: boolean; onChange: (value: boolean) => void }) {
  return (
    <label className="checkbox">
      <input type="checkbox" checked={checked} onChange={(e) => onChange(e.target.checked)} />
      <span>{label}</span>
    </label>
  );
}

export function PageHeader({ title, description, actions }: { title: string; description?: ReactNode; actions?: ReactNode }) {
  return (
    <header className="page-header">
      <div>
        <h1>{title}</h1>
        {description ? <p className="muted">{description}</p> : null}
      </div>
      {actions ? <div className="page-actions">{actions}</div> : null}
    </header>
  );
}

export function Panel({ title, actions, children }: { title?: string; actions?: ReactNode; children: ReactNode }) {
  return (
    <section className="panel">
      {title || actions ? (
        <div className="panel-head">
          {title ? <h2>{title}</h2> : <span />}
          {actions}
        </div>
      ) : null}
      {children}
    </section>
  );
}

export function Loading({ text = 'Загружаем…' }: { text?: string }) {
  return (
    <div className="loading">
      <span className="spinner" aria-hidden /> {text}
    </div>
  );
}

export function ErrorBox({ error, retry }: { error: unknown; retry?: () => void }) {
  if (!error) return null;
  return (
    <div className="error-box" role="alert">
      <span>{errorText(error)}</span>
      {retry ? (
        <Button size="sm" onClick={retry}>
          Повторить
        </Button>
      ) : null}
    </div>
  );
}

export function Empty({ title, children }: { title: string; children?: ReactNode }) {
  return (
    <div className="empty">
      <strong>{title}</strong>
      {children ? <p className="muted">{children}</p> : null}
    </div>
  );
}

export function Badge({ children, tone = 'neutral' }: { children: ReactNode; tone?: 'neutral' | 'good' | 'warn' | 'bad' | 'info' }) {
  return <span className={cn('badge', `badge-${tone}`)}>{children}</span>;
}

export function Tabs<T extends string>({ value, onChange, items }: { value: T; onChange: (v: T) => void; items: { key: T; label: ReactNode }[] }) {
  return (
    <div className="tabs" role="tablist">
      {items.map((item) => (
        <button key={item.key} type="button" role="tab" aria-selected={value === item.key} className={cn('tab', value === item.key && 'tab-active')} onClick={() => onChange(item.key)}>
          {item.label}
        </button>
      ))}
    </div>
  );
}

export function Pagination({ page, total, pageSize, onPage }: { page: number; total: number; pageSize: number; onPage: (p: number) => void }) {
  const pages = Math.max(1, Math.ceil(total / pageSize));
  if (pages <= 1) return null;
  return (
    <div className="pagination">
      <Button size="sm" disabled={page <= 1} onClick={() => onPage(page - 1)}>
        ← Назад
      </Button>
      <span className="muted">
        {page} из {pages} · всего {total.toLocaleString('ru-RU')}
      </span>
      <Button size="sm" disabled={page >= pages} onClick={() => onPage(page + 1)}>
        Вперёд →
      </Button>
    </div>
  );
}

export function Modal({ title, onClose, children, wide }: { title: string; onClose: () => void; children: ReactNode; wide?: boolean }) {
  useEffect(() => {
    const close = (e: KeyboardEvent) => e.key === 'Escape' && onClose();
    window.addEventListener('keydown', close);
    return () => window.removeEventListener('keydown', close);
  }, [onClose]);
  return (
    <div className="modal-backdrop" onMouseDown={(e) => e.target === e.currentTarget && onClose()}>
      <div className={cn('modal', wide && 'modal-wide')} role="dialog" aria-modal aria-label={title}>
        <div className="modal-head">
          <h2>{title}</h2>
          <button type="button" className="icon-btn" aria-label="Закрыть" onClick={onClose}>
            <X size={18} />
          </button>
        </div>
        <div className="modal-body">{children}</div>
      </div>
    </div>
  );
}

// ── уведомления ──

interface Toast {
  id: number;
  text: string;
  tone: 'good' | 'bad';
}

const ToastContext = createContext<(text: string, tone?: 'good' | 'bad') => void>(() => undefined);

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);
  const push = useCallback((text: string, tone: 'good' | 'bad' = 'good') => {
    const id = Date.now() + Math.random();
    setToasts((all) => [...all, { id, text, tone }]);
    window.setTimeout(() => setToasts((all) => all.filter((t) => t.id !== id)), tone === 'bad' ? 7000 : 3500);
  }, []);
  return (
    <ToastContext.Provider value={push}>
      {children}
      <div className="toasts" aria-live="polite">
        {toasts.map((t) => (
          <div key={t.id} className={cn('toast', `toast-${t.tone}`)}>
            {t.text}
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  );
}

export const useToast = () => useContext(ToastContext);

export function formatDate(value?: string | null, withTime = true): string {
  if (!value) return '—';
  const date = new Date(value);
  return withTime
    ? date.toLocaleString('ru-RU', { day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit' })
    : date.toLocaleDateString('ru-RU');
}

export function useDebounced<T>(value: T, ms = 350): T {
  const [current, setCurrent] = useState(value);
  useEffect(() => {
    const timer = window.setTimeout(() => setCurrent(value), ms);
    return () => window.clearTimeout(timer);
  }, [value, ms]);
  return current;
}
