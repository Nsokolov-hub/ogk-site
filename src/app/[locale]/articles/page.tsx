import type { Metadata } from 'next';
import { ArrowRight } from 'lucide-react';
import { getFormatter, getTranslations, setRequestLocale } from 'next-intl/server';
import type { Locale } from '@/i18n/routing';
import type { BreadcrumbItem } from '@/types/content';
import { PageHeader } from '@/components/content/PageHeader';
import { breadcrumbsLd, JsonLd } from '@/components/seo/JsonLd';
import { Container } from '@/components/ui/Container';
import { Link } from '@/i18n/navigation';
import { getArticles } from '@/lib/content-api';
import { pageMetadata, SITE_URL } from '@/lib/seo';

type Props = { params: Promise<{ locale: Locale }> };

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { locale } = await params;
  const t = await getTranslations({ locale, namespace: 'articles.list' });
  return pageMetadata({ locale, path: '/articles/', title: t('title'), description: t('description') });
}

/** Список статей (ТЗ 4.1, 10.4): свежая — крупно, остальные — колонкой ниже */
export default async function ArticlesPage({ params }: Props) {
  const { locale } = await params;
  setRequestLocale(locale);
  const t = await getTranslations('articles');
  const tc = await getTranslations('catalog');
  const format = await getFormatter();
  const list = await getArticles(locale);
  const breadcrumbs: BreadcrumbItem[] = [{ label: tc('home'), href: '/' }, { label: t('list.breadcrumb') }];
  const date = (d: string) => format.dateTime(new Date(d), { day: 'numeric', month: 'long', year: 'numeric' });
  const [first, ...rest] = list;

  return (
    <>
      <JsonLd data={breadcrumbsLd(breadcrumbs, SITE_URL, locale, '/articles/')} />
      <Container>
        <PageHeader breadcrumbs={breadcrumbs} title={t('list.h1')} lead={t('list.lead')} size="h1" />

        {first ? (
          <article className="group relative mt-12 grid gap-6 rounded-block bg-surface p-6 transition-colors hover:bg-surface-strong md:p-10 lg:mt-16 lg:grid-cols-[minmax(0,7fr)_minmax(0,4fr)] lg:gap-16 lg:p-14">
            <div>
              <h2 className="text-h2 font-medium text-text">
                <Link href={`/articles/${first.slug}/`} className="transition-colors after:absolute after:inset-0 after:rounded-[inherit] group-hover:text-accent">
                  {first.h1}
                </Link>
              </h2>
              <p className="mt-5 max-w-[60ch] text-lead text-text">{first.lead}</p>
            </div>
            <div className="flex flex-col justify-end gap-2 text-small text-text-secondary lg:items-end lg:text-right">
              <p>
                <time dateTime={first.publishedAt}>{date(first.publishedAt)}</time>
              </p>
              <p>{t('readingTime', { minutes: first.readingMinutes })}</p>
              <span className="mt-3 inline-flex items-center gap-2 text-body font-semibold text-accent">
                {t('list.read')}
                <ArrowRight aria-hidden size={18} strokeWidth={1.5} className="transition-transform group-hover:translate-x-1" />
              </span>
            </div>
          </article>
        ) : null}

        <ul className="mt-4 grid gap-4 md:mt-6 md:grid-cols-2 md:gap-6">
          {rest.map((a) => (
            <li key={a.slug}>
              <article className="group relative flex h-full flex-col gap-4 rounded-block p-6 transition-colors hover:bg-surface md:p-8">
                <h2 className="text-h3 font-medium text-text">
                  <Link href={`/articles/${a.slug}/`} className="transition-colors after:absolute after:inset-0 after:rounded-[inherit] group-hover:text-accent">
                    {a.h1}
                  </Link>
                </h2>
                <p className="text-body text-text-secondary md:text-lg">{a.lead}</p>
                <p className="mt-auto pt-2 text-small text-text-secondary">
                  <time dateTime={a.publishedAt}>{date(a.publishedAt)}</time> · {t('readingTime', { minutes: a.readingMinutes })}
                </p>
              </article>
            </li>
          ))}
        </ul>
      </Container>
    </>
  );
}
