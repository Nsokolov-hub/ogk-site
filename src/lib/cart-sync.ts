'use client';

import { api } from './backend';
import { useRfqStore, type RfqItem } from './rfq-store';

/**
 * Серверная копия корзины гостя по анонимному cookie на 90 дней (RFQ-01); localStorage остаётся основной копией.
 * После загрузки страницы недостающие строки берутся с сервера (браузер очистил хранилище), дальше каждое
 * изменение уходит на сервер с задержкой в секунду.
 */
let started = false;

export async function startCartSync(): Promise<() => void> {
  if (started) return () => undefined;
  started = true;
  try {
    const server = await api<{ items: RfqItem[] }>('/public/cart', undefined, { revalidate: false });
    const local = useRfqStore.getState().items;
    const known = new Set(local.map((i) => i.key));
    const missing = (server.items ?? []).filter((i) => i && typeof i.key === 'string' && !known.has(i.key));
    if (missing.length) useRfqStore.setState({ items: [...local, ...missing].slice(0, 200) });
  } catch {
    // Сервер недоступен — корзина работает из localStorage
  }
  let timer: ReturnType<typeof setTimeout> | undefined;
  let last = JSON.stringify(useRfqStore.getState().items);
  const push = () => {
    const items = useRfqStore.getState().items;
    const body = JSON.stringify(items);
    if (body === last) return;
    last = body;
    void api('/public/cart', undefined, { method: 'PUT', body: { items: items.slice(0, 200) }, revalidate: false }).catch(() => {
      last = '';
    });
  };
  push();
  const unsubscribe = useRfqStore.subscribe(() => {
    clearTimeout(timer);
    timer = setTimeout(push, 1000);
  });
  return () => {
    clearTimeout(timer);
    unsubscribe();
    started = false;
  };
}
