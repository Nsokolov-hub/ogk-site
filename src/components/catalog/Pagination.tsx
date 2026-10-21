import { useTranslations } from 'next-intl';
import { Link } from '@/i18n/navigation';
import { catalogHref, type CatalogQuery } from '@/lib/catalog';
import { cn } from '@/lib/cn';

/** Номера страниц с многоточиями: 1 … 4 5 [6] 7 8 … 20 */
function pageList(current: number, total: number): (number | 'gap')[] {
  const set = new Set([1, total, current - 2, current - 1, current, current + 1, current + 2].filter((p) => p >= 1 && p <= total));
  const sorted = Array.from(set).sort((a, b) => a - b);
  const out: (number | 'gap')[] = [];
  sorted.forEach((p, i) => {
    if (i > 0 && p - sorted[i - 1] > 1) out.push('gap');
    out.push(p);
  });
  return out;
}

/**
 * Пагинация (ТЗ 11.2): «Предыдущая», номера, «Следующая», «Последняя». Обычные ссылки — для роботов (SEO-09).
 * start…end — диапазон уже показанных страниц (после «Показать ещё» их несколько).
 */
export function Pagination({
  basePath,
  query,
  start,
  end,
  pageCount,
}: {
  basePath: string;
  query: CatalogQuery;
  start: number;
  end: number;
  pageCount: number;
}) {
  const t = useTranslations('catalog');
  if (pageCount <= 1) return null;
  const href = (page: number) => catalogHref(basePath, { filters: query.filters, sort: query.sort, page });
  const item = 'inline-grid h-10 min-w-10 place-items-center rounded-pill px-3 text-small font-medium transition-colors';
  const link = `${item} text-text hover:bg-surface-strong hover:text-accent`;
  const disabled = `${item} text-text-secondary/50`;

  return (
    <nav aria-label={t('pagination')} className="mt-8">
      <ul className="flex flex-wrap items-center justify-center gap-1">
        <li>
          {start > 1 ? (
            <Link href={href(start - 1)} rel="prev" scroll={false} className={link}>
              {t('prev')}
            </Link>
          ) : (
            <span className={disabled}>{t('prev')}</span>
          )}
        </li>
        {pageList(end, pageCount).map((p, i) =>
          p === 'gap' ? (
            <li key={`gap-${i}`} aria-hidden className="px-1 text-text-secondary">
              …
            </li>
          ) : (
            <li key={p}>
              {p >= start && p <= end ? (
                <span
                  aria-current={p === end ? 'page' : undefined}
                  className={cn(item, 'bg-accent text-text-on-accent')}
                >
                  <span className="sr-only">{t('page', { n: p })}: </span>
                  {p}
                </span>
              ) : (
                <Link href={href(p)} scroll={false} aria-label={t('page', { n: p })} className={link}>
                  {p}
                </Link>
              )}
            </li>
          ),
        )}
        <li>
          {end < pageCount ? (
            <Link href={href(end + 1)} rel="next" scroll={false} className={link}>
              {t('next')}
            </Link>
          ) : (
            <span className={disabled}>{t('next')}</span>
          )}
        </li>
        <li>
          {end < pageCount ? (
            <Link href={href(pageCount)} scroll={false} className={link}>
              {t('last')}
            </Link>
          ) : (
            <span className={disabled}>{t('last')}</span>
          )}
        </li>
      </ul>
    </nav>
  );
}
