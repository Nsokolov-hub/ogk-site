import type { Metadata } from 'next';
import { notFound } from 'next/navigation';
import { getTranslations, setRequestLocale } from 'next-intl/server';
import type { Locale } from '@/i18n/routing';
import type { BreadcrumbItem } from '@/types/content';
import { PageHeader } from '@/components/content/PageHeader';
import { breadcrumbsLd, JsonLd, personLd } from '@/components/seo/JsonLd';
import { Container } from '@/components/ui/Container';
import { Link } from '@/i18n/navigation';
import { getArticles, getAuthor } from '@/lib/content-api';
import { absoluteUrl, pageMetadata, SITE_URL } from '@/lib/seo';

type Props = { params: Promise<{ locale: Locale; slug: string }> };

/** Страница автора (ТЗ 10.4). Пока нет квалификации и фото — noindex, follow: пустой профиль не помогает E-E-A-T */
export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { locale, slug } = await params;
  const a = await getAuthor(slug);
  if (!a) return {};
  const t = await getTranslations({ locale, namespace: 'articles.authorPage' });
  return pageMetadata({
    locale,
    path: `/authors/${a.slug}/`,
    title: t('title', { name: a.name }),
    description: t('description', { name: a.name }),
    index: !!a.bio?.length,
  });
}

export default async function AuthorPage({ params }: Props) {
  const { locale, slug } = await params;
  setRequestLocale(locale);
  const author = await getAuthor(slug);
  if (!author) notFound();
  const t = await getTranslations('articles');
  const tc = await getTranslations('catalog');
  const list = (await getArticles(locale)).filter((a) => a.authorSlug === author.slug);
  const path = `/authors/${author.slug}/`;
  const breadcrumbs: BreadcrumbItem[] = [
    { label: tc('home'), href: '/' },
    { label: t('list.breadcrumb'), href: '/articles/' },
    { label: author.name },
  ];

  return (
    <>
      <JsonLd data={[breadcrumbsLd(breadcrumbs, SITE_URL, locale, path), personLd({ url: absoluteUrl(locale, path), name: author.name, jobTitle: author.role, siteUrl: SITE_URL })]} />
      <Container>
        <PageHeader breadcrumbs={breadcrumbs} title={author.name} lead={author.role} />
        {author.bio?.length ? (
          <div className="mt-8 flex max-w-[72ch] flex-col gap-4 text-body text-text md:text-lg">
            {author.bio.map((p) => (
              <p key={p.slice(0, 32)}>{p}</p>
            ))}
          </div>
        ) : null}

        <section aria-labelledby="author-articles" className="mt-16 lg:mt-20">
          <h2 id="author-articles" className="text-h3 font-medium text-text">
            {t('authorPage.articles')}
          </h2>
          <ul className="mt-6 flex flex-col gap-2">
            {list.map((a) => (
              <li key={a.slug}>
                <Link href={`/articles/${a.slug}/`} className="group block rounded-block px-6 py-5 transition-colors hover:bg-surface md:px-8">
                  <span className="block text-h4 font-medium text-text transition-colors group-hover:text-accent">{a.h1}</span>
                  <span className="mt-1 block text-body text-text-secondary">{a.lead}</span>
                </Link>
              </li>
            ))}
          </ul>
        </section>
      </Container>
    </>
  );
}
