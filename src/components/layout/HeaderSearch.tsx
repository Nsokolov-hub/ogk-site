'use client';

import { SearchBox } from '@/components/search/SearchBox';

/** Строка поиска в шапке (SRCH-01): GET-форма на /search/ с подсказками после 2 символов; header — вид из макета капсулы */
export function HeaderSearch({ autoFocus, className, variant = 'md' }: { autoFocus?: boolean; className?: string; variant?: 'md' | 'header' }) {
  return <SearchBox size={variant} autoFocus={autoFocus} place="header" className={className} />;
}
