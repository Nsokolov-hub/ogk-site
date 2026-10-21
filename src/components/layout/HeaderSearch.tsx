'use client';

import { SearchBox } from '@/components/search/SearchBox';

/** Строка поиска в шапке (SRCH-01): GET-форма на /search/ с подсказками после 2 символов */
export function HeaderSearch({ autoFocus, className }: { autoFocus?: boolean; className?: string }) {
  return <SearchBox size="md" autoFocus={autoFocus} place="header" className={className} />;
}
