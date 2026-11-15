'use client';

import { create } from 'zustand';
import type { ProductPreview } from '@/types/catalog';
import { track } from './analytics';
import { defaultProductSelection, type ProductSelection } from './product-selection';

/** Одно окно «Заказать в 1 клик» на всё приложение (RFQ-04) */
interface OneClickState {
  isOpen: boolean;
  product: ProductPreview | null;
  packagingId: string | null;
  selection: ProductSelection | null;
  drafts: Record<string, ProductSelection>;
  setDraft: (productId: string, selection: ProductSelection) => void;
  /** Куда вернуть фокус после закрытия */
  trigger: HTMLElement | null;
  open: (p: { product: ProductPreview; packagingId?: string | null; selection?: ProductSelection; trigger?: HTMLElement | null }) => void;
  close: () => void;
}

export const useOneClickStore = create<OneClickState>()((set) => ({
  isOpen: false,
  product: null,
  packagingId: null,
  selection: null,
  drafts: {},
  setDraft: (productId, selection) => set((s) => ({ drafts: { ...s.drafts, [productId]: selection } })),
  trigger: null,
  open: ({ product, packagingId, selection, trigger = null }) => {
    const choice = selection ?? defaultProductSelection(product, packagingId);
    set({ isOpen: true, product, packagingId: choice.packagingId, selection: choice, trigger });
    track('request_open', { form_type: 'one_click', sku: product.catalogNumber, brand: product.brand.name });
  },
  close: () => set({ isOpen: false }),
}));
