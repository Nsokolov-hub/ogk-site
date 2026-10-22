'use client';

import type { MouseEvent } from 'react';
import { create } from 'zustand';

/** Выдвижная панель корзины запроса (RFQ-01): одна на сайт, открывается из шапки и с кнопок «В корзине» */
export const useCartDrawer = create<{ open: boolean; setOpen: (open: boolean) => void }>()((set) => ({
  open: false,
  setOpen: (open) => set({ open }),
}));

/**
 * Обработчик для ссылок на /rfq/: обычный клик открывает панель, клик с модификатором или средней кнопкой
 * открывает страницу корзины как обычная ссылка. Без JavaScript ссылка просто ведёт на /rfq/.
 */
export function openCartDrawer(e: MouseEvent<HTMLAnchorElement>) {
  if (e.defaultPrevented || e.button !== 0 || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;
  e.preventDefault();
  useCartDrawer.getState().setOpen(true);
}
