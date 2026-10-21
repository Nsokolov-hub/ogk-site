import type { Metadata } from 'next';
import { notFound } from 'next/navigation';
import { BadgeCheck } from 'lucide-react';
import { getFormatter, getTranslations, setRequestLocale } from 'next-intl/server';
import type { Locale } from '@/i18n/routing';
import type { BreadcrumbItem } from '@/types/content';
import { ArticleBody } from '@/components/content/ArticleBody';
import { LinkChips } from '@/components/content/LinkChips';
import { Breadcrumbs } from '@/components/layout/Breadcrumbs';
import { articleLd, breadcrumbsLd, JsonLd } from '@/components/seo/JsonLd';
import { Button } from '@/components/ui/Button';
import { Container } from '@/components/ui/Container';
import { Link } from '@/i18n/navigation';
import { getArticle, getArticles, getAuthor } from '@/lib/content-api';
import { absoluteUrl, pageMetadata, SITE_URL } from '@/lib/seo';

type Props = { params: Promise<{ locale: Locale; slug: string }> };

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { locale, slug } = await params;
  const a = await getArticle(slug, locale);
  if (!a) return {};
  const author = await getAuthor(a.authorSlug);
  return pageMetadata({
    locale,
    path: `/articles/${a.slug}/`,
    title: a.title,
    description: a.description,
    hasEn: a.hasEn,
    ogType: 'article',
    article: { publishedTime: a.publishedAt, modifiedTime: a.updatedAt, authors: author ? [author.name] : [] },
  });
}

/** Статья (ТЗ 10.4): автор, даты публикации и обновления, оглавление, ссылки на каталог и услуги, спокойный CTA */
export default async function ArticlePage({ params }: Props) {
  const { locale, slug } = await params;
  setRequestLocale(locale);
  const a = await getArticle(slug, locale);
  if (!a) notFound();
  const [author, all] = await Promise.all([getAuthor(a.authorSlug), getArticles(locale)]);
  const t = await getTranslations('articles');
  const tc = await getTranslations('catalog');
  const format = await getFormatter();
  const date = (d: string) => format.dateTime(new Date(d), { day: 'numeric', month: 'long', year: 'numeric' });
  const path = `/articles/${a.slug}/`;
  const authorPath = author ? `/authors/${author.slug}/` : undefined;

  const breadcrumbs: BreadcrumbItem[] = [
    { label: tc('home'), href: '/' },
    { label: t('list.breadcrumb'), href: '/articles/' },
    { label: a.h1 },
  ];
  const toc = a.body.filter((b): b is Extract<typeof b, { type: 'h2' }> => b.type === 'h2');
  const more = all.filter((x) => x.slug !== a.slug).slice(0, 2);

  return (
    <>
      <JsonLd
        data={[
          breadcrumbsLd(breadcrumbs, SITE_URL, locale, path),
          articleLd({
            url: absoluteUrl(locale, path),
            headline: a.h1,
            description: a.description,
            datePublished: a.publishedAt,
            dateModified: a.updatedAt,
            author: { name: author?.name ?? 'ОГК-ХИМ', url: authorPath ? absoluteUrl(locale, authorPath) : `${SITE_URL}/`, jobTitle: author?.role },
            siteUrl: SITE_URL,
          }),
        ]}
      />
      <Container className="pt-24 lg:pt-[150px]">
        <Breadcrumbs items={breadcrumbs} />

        <header className="mt-8 max-w-[960px]">
          <h1 className="text-h1 font-medium text-text">{a.h1}</h1>
          <p className="mt-5 max-w-[68ch] text-lead text-text">{a.lead}</p>
          <div className="mt-8 flex flex-wrap items-center gap-x-6 gap-y-2 text-small text-text-secondary">
            {author ? (
              <p>
                {t('author')}:{' '}
                <Link href={authorPath!} className="text-text underline-offset-2 hover:text-accent hover:underline">
                  {author.name}
                </Link>
              </p>
            ) : null}
            <p>
              {t('published')} <time dateTime={a.publishedAt}>{date(a.publishedAt)}</time>
            </p>
            {a.updatedAt !== a.publishedAt ? (
              <p>
                {t('updated')} <time dateTime={a.updatedAt}>{date(a.updatedAt)}</time>
              </p>
            ) : null}
            <p>{t('readingTime', { minutes: a.readingMinutes })}</p>
            {a.reviewed ? (
              <p className="inline-flex items-center gap-1.5 text-accent">
                <BadgeCheck aria-hidden size={18} strokeWidth={1.5} />
                {t('reviewed')}
              </p>
            ) : null}
          </div>
        </header>

        <div className="mt-14 grid gap-12 lg:mt-20 lg:grid-cols-[minmax(0,3fr)_minmax(0,8fr)] lg:gap-16 2xl:grid-cols-[minmax(0,3fr)_minmax(0,7fr)_minmax(0,2fr)]">
          {/* Оглавление: на десктопе прилипает слева */}
          <nav aria-label={t('toc')} className="lg:sticky lg:top-28 lg:self-start">
            <p className="text-body font-medium text-text">{t('toc')}</p>
            <ol className="mt-4 flex flex-col gap-1 border-l-0">
              {toc.map((h) => (
                <li key={h.id}>
                  <a href={`#${h.id}`} className="block rounded-sm py-1.5 text-body text-text-secondary transition-colors hover:text-accent">
                    {h.text}
                  </a>
                </li>
              ))}
            </ol>
          </nav>

          <div className="min-w-0 max-w-[72ch]">
            <ArticleBody blocks={a.body} />

            <LinkChips id="article-links" title={t('links')} items={a.links} className="mt-16" />

            {/* Спокойный CTA в конце статьи */}
            <aside aria-labelledby="article-cta" className="mt-16 rounded-block bg-surface p-6 md:p-10">
              <h2 id="article-cta" className="text-h3 font-medium text-text">
                {a.cta.title}
              </h2>
              <p className="mt-3 text-body text-text-secondary md:text-lg">{a.cta.text}</p>
              <Button href={a.cta.href} size="m" className="mt-6">
                {a.cta.label}
              </Button>
            </aside>

            {author ? (
              <section aria-labelledby="article-author" className="mt-16 flex items-center gap-5">
                <span aria-hidden className="grid size-16 shrink-0 place-items-center rounded-full bg-surface-strong text-h4 font-medium text-accent">
                  {author.name
                    .split(' ')
                    .slice(0, 2)
                    .map((w) => w[0])
                    .join('')}
                </span>
                <div>
                  <h2 id="article-author" className="text-body font-medium text-text">
                    <Link href={authorPath!} className="transition-colors hover:text-accent">
                      {author.name}
                    </Link>
                  </h2>
                  <p className="text-small text-text-secondary">{author.role}</p>
                </div>
              </section>
            ) : null}
          </div>
        </div>

        {more.length ? (
          <section aria-labelledby="more-articles" className="mt-20 lg:mt-28">
            <h2 id="more-articles" className="text-h3 font-medium text-text">
              {t('more')}
            </h2>
            <ul className="mt-6 grid gap-4 md:grid-cols-2 md:gap-6">
              {more.map((m) => (
                <li key={m.slug}>
                  <Link href={`/articles/${m.slug}/`} className="group flex h-full flex-col gap-3 rounded-block bg-surface p-6 transition-colors hover:bg-surface-strong md:p-8">
                    <span className="text-h4 font-medium text-text transition-colors group-hover:text-accent">{m.h1}</span>
                    <span className="text-body text-text-secondary">{m.lead}</span>
                  </Link>
                </li>
              ))}
            </ul>
          </section>
        ) : null}
      </Container>
    </>
  );
}
