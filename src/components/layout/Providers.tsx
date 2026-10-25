'use client';

import { useEffect } from 'react';
import { startCartSync } from '@/lib/cart-sync';
import { useRfqStore } from '@/lib/rfq-store';

/** Восстанавливает корзину запроса из хранилища, синхронизирует вкладки и серверную копию (RFQ-01) */
export function Providers() {
  useEffect(() => {
    let stopSync: (() => void) | undefined;
    void Promise.resolve(useRfqStore.persist.rehydrate()).then(async () => {
      stopSync = await startCartSync();
    });
    const onStorage = (e: StorageEvent) => {
      if (e.key === 'ogk-rfq') void useRfqStore.persist.rehydrate();
    };
    window.addEventListener('storage', onStorage);
    return () => {
      window.removeEventListener('storage', onStorage);
      stopSync?.();
    };
  }, []);

  return null;
}
