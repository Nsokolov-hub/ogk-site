'use client';

import { create } from 'zustand';
import { createJSONStorage, persist } from 'zustand/middleware';
import type { PackUnit } from '@/types/catalog';
import type { Analogue } from '@/types/requests';

/**
 * Корзина запроса КП (RFQ-01, RFQ-02).
 * Сейчас хранится в localStorage; серверная копия по анонимному cookie — вместе с API.
 */
export interface RfqItem {
  key: string;
  productId: string;
  slug: string;
  name: string;
  brand: string;
  catalogNumber: string;
  cas?: string;
  categorySlug?: string;
  packagingId: string | null;
  packagingLabel?: string;
  customPackaging?: { amount: number; unit: PackUnit };
  quantity: number;
  analogue: Analogue;
  comment?: string;
  addedAt: number;
}

export type RfqItemInput = Omit<RfqItem, 'key' | 'addedAt'>;

interface RfqState {
  items: RfqItem[];
  hydrated: boolean;
  add: (item: RfqItemInput) => void;
  remove: (key: string) => void;
  setQuantity: (key: string, quantity: number) => void;
  setAnalogue: (key: string, analogue: Analogue) => void;
  clear: () => void;
}

export const rfqKey = (productId: string, packagingId: string | null) => `${productId}:${packagingId ?? 'custom'}`;

export const useRfqStore = create<RfqState>()(
  persist(
    (set) => ({
      items: [],
      hydrated: false,
      add: (input) =>
        set((s) => {
          const key = rfqKey(input.productId, input.packagingId);
          const existing = s.items.find((i) => i.key === key);
          if (existing) {
            return {
              items: s.items.map((i) => (i.key === key ? { ...i, quantity: Math.min(999, i.quantity + input.quantity) } : i)),
            };
          }
          return { items: [...s.items, { ...input, key, addedAt: Date.now() }] };
        }),
      remove: (key) => set((s) => ({ items: s.items.filter((i) => i.key !== key) })),
      setQuantity: (key, quantity) =>
        set((s) => ({
          items: s.items.map((i) => (i.key === key ? { ...i, quantity: Math.max(1, Math.min(999, quantity)) } : i)),
        })),
      setAnalogue: (key, analogue) =>
        set((s) => ({ items: s.items.map((i) => (i.key === key ? { ...i, analogue } : i)) })),
      clear: () => set({ items: [] }),
    }),
    {
      name: 'ogk-rfq',
      version: 1,
      storage: createJSONStorage(() => localStorage),
      partialize: (s) => ({ items: s.items }),
      // Восстанавливаем вручную после монтирования — так нет расхождений с серверным HTML
      skipHydration: true,
      onRehydrateStorage: () => () => {
        useRfqStore.setState({ hydrated: true });
      },
    },
  ),
);

/** Сколько позиций в корзине (строк, не упаковок) */
export const selectRfqCount = (s: RfqState) => s.items.length;
