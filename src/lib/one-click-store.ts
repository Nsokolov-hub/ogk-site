'use client';

import { create } from 'zustand';
import type { ProductPreview } from '@/types/catalog';

/** Одно окно «Заказать в 1 клик» на всё приложение (RFQ-04) */
interface OneClickState {
  isOpen: boolean;
  product: ProductPreview | null;
  packagingId: string | null;
  /** Куда вернуть фокус после закрытия */
  trigger: HTMLElement | null;
  open: (p: { product: ProductPreview; packagingId: string | null; trigger?: HTMLElement | null }) => void;
  close: () => void;
}

export const useOneClickStore = create<OneClickState>()((set) => ({
  isOpen: false,
  product: null,
  packagingId: null,
  trigger: null,
  open: ({ product, packagingId, trigger = null }) => set({ isOpen: true, product, packagingId, trigger }),
  close: () => set({ isOpen: false }),
}));
