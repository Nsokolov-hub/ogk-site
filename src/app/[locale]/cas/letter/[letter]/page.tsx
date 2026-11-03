import type { Metadata } from 'next';
import { notFound } from 'next/navigation';
import { getTranslations, setRequestLocale } from 'next-intl/server';
import type { Locale } from '@/i18n/routing';
import type { BreadcrumbItem } from '@/types/content';
import { PageHeader } from '@/components/content/PageHeader';
import { breadcrumbsLd, JsonLd } from '@/components/seo/JsonLd';
import { Container } from '@/components/ui/Container';
import { Link } from '@/i18n/navigation';
import { cn } from '@/lib/cn';
import { casLabel, getCasIndex, getCasLetter } from '@/lib/product-api';
import { pageMetadata, SITE_URL } from '@/lib/seo';

type Props = { params: Promise<{ locale: Locale; letter: string }>; searchParams: Promise<{ page?: string }> };

const pageOf = (raw?: string) => {
  const n = Number(raw ?? '1');
  return Number.isInteger(n) && n >= 1 ? n : NaN;
};

export async function generateMetadata({ params, searchParams }: Props): Promise<Metadata> {
  const { locale, letter } = await params;
  const page = pageOf((await searchParams).page);
  const t = await getTranslations({ locale, namespace: 'casIndex' });
  const data = Number.isNaN(page) ? null : await getCasLetter(letter, page);
  if (!data) return {};
  const label = data.letter === '0' ? t('other') : data.letter.toUpperCase();
  const suffix = data.page > 1 ? t('meta.page', { page: data.page }) : '';
  return pageMetadata({
    locale,
    path: `/cas/letter/${data.letter}/`,
    canonicalQuery: data.page > 1 ? `page=${data.page}` : undefined,
    title: `${t('meta.letterTitle', { letter: label, count: data.total })}${suffix} | ${t('meta.brand')}`,
    description: t('meta.letterDescription', { letter: label, count: data.total, first: data.items[0]?.name ?? '' }),
    hasEn: true,
  });
}

/** Буква указателя: названия по алфавиту, по 500 на странице, со ссылками на страницы CAS */
export default async function CasLetterPage({ params, searchParams }: Props) {
  const { locale, letter } = await params;
  setRequestLocale(locale);
  const page = pageOf((await searchParams).page);
  if (Number.isNaN(page)) notFound();
  const [data, index] = await Promise.all([getCasLetter(letter, page), getCasIndex()]);
  if (!data || data.letter !== letter) notFound();
  const t = await getTranslations('casIndex');
  const tc = await getTranslations('catalog');
  const label = data.letter === '0' ? t('other') : data.letter.toUpperCase();
  const path = `/cas/letter/${data.letter}/`;
  const breadcrumbs: BreadcrumbItem[] = [
    { label: tc('home'), href: '/' },
    { label: t('breadcrumb'), href: '/cas/' },
    { label: label },
  ];
  const href = (n: number) => (n > 1 ? `${path}?page=${n}` : path);

  return (
    <>
      <JsonLd data={breadcrumbsLd(breadcrumbs, SITE_URL, locale, path)} />
      <Container>
        <PageHeader
          breadcrumbs={breadcrumbs}
          title={t('letterH1', { letter: label })}
          lead={t('letterLead', { count: data.total, page: data.page, pages: data.pageCount })}
        />

        <nav aria-label={t('letters')} className="mt-10">
          <ul className="flex flex-wrap gap-2">
            {index.letters.map((l) => (
              <li key={l.letter}>
                <Link
                  href={`/cas/letter/${l.letter}/`}
                  aria-current={l.letter === data.letter ? 'page' : undefined}
                  className={cn(
                    'inline-flex h-11 min-w-11 items-center justify-center rounded-full px-4 text-body font-medium transition-colors',
                    l.letter === data.letter ? 'bg-accent text-text-on-accent' : 'bg-surface-strong text-text hover:text-accent',
                  )}
                >
                  {l.letter === '0' ? t('other') : l.letter.toUpperCase()}
                </Link>
              </li>
            ))}
          </ul>
        </nav>

        <ul className="mt-12 columns-1 gap-10 sm:columns-2 lg:columns-3">
          {data.items.map((c) => (
            <li key={c.cas} className="break-inside-avoid">
              <Link href={`/cas/${c.cas}/`} className="group flex items-baseline justify-between gap-4 rounded-sm py-1.5 text-body text-text transition-colors hover:text-accent">
                <span className="chem-wrap min-w-0">{casLabel(c, locale)}</span>
                <span className="shrink-0 text-small tabular-nums text-text-secondary group-hover:text-accent">{c.cas}</span>
              </Link>
            </li>
          ))}
        </ul>

        {data.pageCount > 1 ? (
          <nav aria-label={t('pages')} className="mt-12">
            <ul className="flex flex-wrap gap-2">
              {Array.from({ length: data.pageCount }, (_, i) => i + 1).map((n) => (
                <li key={n}>
                  <Link
                    href={href(n)}
                    aria-current={n === data.page ? 'page' : undefined}
                    className={cn(
                      'inline-grid size-11 place-items-center rounded-full text-body tabular-nums transition-colors',
                      n === data.page ? 'bg-accent text-text-on-accent' : 'bg-surface-strong text-text hover:text-accent',
                    )}
                  >
                    {n}
                  </Link>
                </li>
              ))}
            </ul>
          </nav>
        ) : null}
      </Container>
    </>
  );
}
