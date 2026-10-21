'use client';

import { useEffect } from 'react';
import { useRfqStore } from '@/lib/rfq-store';

/** Восстанавливает корзину запроса из хранилища после монтирования и синхронизирует вкладки */
export function Providers() {
  useEffect(() => {
    void useRfqStore.persist.rehydrate();
    const onStorage = (e: StorageEvent) => {
      if (e.key === 'ogk-rfq') void useRfqStore.persist.rehydrate();
    };
    window.addEventListener('storage', onStorage);
    return () => window.removeEventListener('storage', onStorage);
  }, []);

  return null;
}
