import { Link } from '@/i18n/navigation';
import { casLabel, type CasRef } from '@/lib/product-api';

/**
 * Ссылки на страницы веществ по CAS (/cas/<cas>/) — в разделах, брендах, на страницах CAS и в указателе.
 * Индексируемые страницы сайта ведут к страницам CAS, иначе поисковик находит их только по Sitemap.
 */
export function CasLinks({ items, locale, offersLabel }: { items: CasRef[]; locale: string; offersLabel?: (count: number) => string }) {
  return (
    <ul className="flex flex-wrap gap-2">
      {items.map((c) => (
        <li key={c.cas} className="max-w-full">
          <Link
            href={`/cas/${c.cas}/`}
            className="inline-flex min-h-11 max-w-full flex-wrap items-baseline gap-x-2 rounded-pill bg-surface-strong px-5 py-2 text-body text-text transition-colors hover:text-accent"
          >
            <span className="chem-wrap min-w-0">{casLabel(c, locale)}</span>
            <span className="text-small tabular-nums text-text-secondary">
              CAS {c.cas}
              {offersLabel ? ` · ${offersLabel(c.offers)}` : ''}
            </span>
          </Link>
        </li>
      ))}
    </ul>
  );
}
