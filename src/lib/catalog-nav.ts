'use client';

import { useEffect, useTransition } from 'react';
import { create } from 'zustand';
import { useRouter } from '@/i18n/navigation';

/** Идёт ли переход между выборками каталога (фильтр, сортировка) — для затемнения списка */
export const useCatalogNav = create<{ pending: boolean; setPending: (v: boolean) => void }>()((set) => ({
  pending: false,
  setPending: (pending) => set({ pending }),
}));

/** Переход на новую выборку без прокрутки страницы, с индикатором загрузки */
export function useCatalogNavigate() {
  const router = useRouter();
  const [isPending, startTransition] = useTransition();
  const setPending = useCatalogNav((s) => s.setPending);

  useEffect(() => {
    setPending(isPending);
  }, [isPending, setPending]);

  return (href: string) => startTransition(() => router.push(href, { scroll: false }));
}

/** База для action GET-форм: работают и без JS */
export function localizedPath(locale: string, path: string) {
  return locale === 'ru' ? path : `/${locale}${path}`;
}
