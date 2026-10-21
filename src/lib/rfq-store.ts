'use client';

import { create } from 'zustand';
import { createJSONStorage, persist } from 'zustand/middleware';
import type { Packaging, PackUnit } from '@/types/catalog';
import type { Analogue } from '@/types/requests';

/**
 * Корзина запроса КП (RFQ-01, RFQ-02, RFQ-12).
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
  /** Фасовки товара — для выбора прямо в корзине */
  packagings?: Packaging[];
  /** У товара доступна своя фасовка (5.2.2) */
  customAllowed?: boolean;
  customPackaging?: { amount: number; unit: PackUnit };
  quantity: number;
  analogue: Analogue;
  comment?: string;
  /** Свободная строка — позиция вне каталога (RFQ-02) */
  free?: boolean;
  addedAt: number;
}

export type RfqItemInput = Omit<RfqItem, 'key' | 'addedAt'>;

export interface FreeItemInput {
  name: string;
  brand?: string;
  catalogNumber?: string;
  cas?: string;
  quantity?: number;
  comment?: string;
}

interface RfqState {
  items: RfqItem[];
  hydrated: boolean;
  add: (item: RfqItemInput) => void;
  addFree: (item: FreeItemInput) => void;
  remove: (key: string) => void;
  setQuantity: (key: string, quantity: number) => void;
  setAnalogue: (key: string, analogue: Analogue) => void;
  setAllAnalogue: (analogue: Analogue) => void;
  setComment: (key: string, comment: string) => void;
  updateFree: (key: string, patch: Partial<FreeItemInput>) => void;
  /** Смена фасовки меняет ключ строки; совпадение с другой строкой — количества складываются */
  setPackaging: (key: string, p: { packagingId: string | null; packagingLabel?: string; customPackaging?: { amount: number; unit: PackUnit } }) => void;
  clear: () => void;
}

export const rfqKey = (productId: string, packagingId: string | null) => `${productId}:${packagingId ?? 'custom'}`;

const clampQty = (n: number) => Math.max(1, Math.min(999, Math.round(n) || 1));

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
              items: s.items.map((i) =>
                i.key === key ? { ...i, ...input, key, quantity: clampQty(i.quantity + input.quantity), addedAt: i.addedAt } : i,
              ),
            };
          }
          return { items: [...s.items, { ...input, key, addedAt: Date.now() }] };
        }),
      addFree: (input) =>
        set((s) => {
          const id = `free-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 7)}`;
          return {
            items: [
              ...s.items,
              {
                key: `${id}:free`,
                productId: id,
                slug: '',
                name: input.name,
                brand: input.brand ?? '',
                catalogNumber: input.catalogNumber ?? '',
                cas: input.cas,
                packagingId: null,
                quantity: clampQty(input.quantity ?? 1),
                analogue: 'none',
                comment: input.comment,
                free: true,
                addedAt: Date.now(),
              },
            ],
          };
        }),
      remove: (key) => set((s) => ({ items: s.items.filter((i) => i.key !== key) })),
      setQuantity: (key, quantity) =>
        set((s) => ({ items: s.items.map((i) => (i.key === key ? { ...i, quantity: clampQty(quantity) } : i)) })),
      setAnalogue: (key, analogue) => set((s) => ({ items: s.items.map((i) => (i.key === key ? { ...i, analogue } : i)) })),
      setAllAnalogue: (analogue) => set((s) => ({ items: s.items.map((i) => ({ ...i, analogue })) })),
      setComment: (key, comment) => set((s) => ({ items: s.items.map((i) => (i.key === key ? { ...i, comment } : i)) })),
      updateFree: (key, patch) =>
        set((s) => ({
          items: s.items.map((i) =>
            i.key === key && i.free
              ? {
                  ...i,
                  ...(patch.name !== undefined ? { name: patch.name } : {}),
                  ...(patch.brand !== undefined ? { brand: patch.brand } : {}),
                  ...(patch.catalogNumber !== undefined ? { catalogNumber: patch.catalogNumber } : {}),
                  ...(patch.cas !== undefined ? { cas: patch.cas } : {}),
                  ...(patch.quantity !== undefined ? { quantity: clampQty(patch.quantity) } : {}),
                }
              : i,
          ),
        })),
      setPackaging: (key, p) =>
        set((s) => {
          const item = s.items.find((i) => i.key === key);
          if (!item) return s;
          const nextKey = rfqKey(item.productId, p.packagingId);
          const updated: RfqItem = { ...item, ...p, key: nextKey, customPackaging: p.packagingId ? undefined : p.customPackaging };
          const clash = nextKey !== key ? s.items.find((i) => i.key === nextKey) : undefined;
          if (clash) {
            return {
              items: s.items
                .filter((i) => i.key !== key)
                .map((i) => (i.key === nextKey ? { ...i, quantity: clampQty(i.quantity + item.quantity) } : i)),
            };
          }
          return { items: s.items.map((i) => (i.key === key ? updated : i)) };
        }),
      clear: () => set({ items: [] }),
    }),
    {
      name: 'ogk-rfq',
      version: 2,
      storage: createJSONStorage(() => localStorage),
      partialize: (s) => ({ items: s.items }),
      migrate: (persisted) => persisted as { items: RfqItem[] },
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
