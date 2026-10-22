import type { Metadata } from 'next';
import { notFound } from 'next/navigation';
import { ArrowRight, CircleCheck, ListPlus } from 'lucide-react';
import { getTranslations, setRequestLocale } from 'next-intl/server';
import type { Locale } from '@/i18n/routing';
import type { BreadcrumbItem } from '@/types/content';
import { FaqSection } from '@/components/content/FaqSection';
import { PageHeader } from '@/components/content/PageHeader';
import { RequestBlock } from '@/components/content/RequestBlock';
import { ProductCard } from '@/components/product/ProductCard';
import { breadcrumbsLd, faqLd, JsonLd } from '@/components/seo/JsonLd';
import { Button } from '@/components/ui/Button';
import { Chip } from '@/components/ui/Chip';
import { Container } from '@/components/ui/Container';
import { Link } from '@/i18n/navigation';
import { getSiteSettings } from '@/lib/api';
import { getSolutionPage } from '@/lib/content-api';
import { pageMetadata, SITE_URL } from '@/lib/seo';

type Props = { params: Promise<{ locale: Locale; slug: string }> };

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { locale, slug } = await params;
  const data = await getSolutionPage(slug, locale);
  if (!data) return {};
  const s = data.solution;
  return pageMetadata({ locale, path: `/solutions/${s.slug}/`, title: s.title, description: s.description, hasEn: s.hasEn });
}

/**
 * Отраслевое решение (ТЗ 4.1): задачи лаборатории → что поставляем (разделы и подборки каталога) →
 * часто заказывают → услуги → статьи → FAQ → заявка. Перелинковка решение → категории → товары (SEO-08).
 */
export default async function SolutionPage({ params }: Props) {
  const { locale, slug } = await params;
  setRequestLocale(locale);
  const [data, settings] = await Promise.all([getSolutionPage(slug, locale), getSiteSettings(locale)]);
  if (!data) notFound();
  const { solution: s, counts, products, services, articles } = data;
  const t = await getTranslations('solutions');
  const tc = await getTranslations('catalog');
  const path = `/solutions/${s.slug}/`;

  const breadcrumbs: BreadcrumbItem[] = [
    { label: tc('home'), href: '/' },
    { label: t('list.breadcrumb'), href: '/solutions/' },
    { label: s.name },
  ];
  const ld: Record<string, unknown>[] = [breadcrumbsLd(breadcrumbs, SITE_URL, locale, path)];
  if (s.faq?.length) ld.push(faqLd(s.faq));
  const h2 = 'text-h2 font-medium text-text';

  return (
    <>
      <JsonLd data={ld} />
      <Container>
        <PageHeader breadcrumbs={breadcrumbs} title={s.h1} lead={s.intro} size="h1">
          <div className="mt-8 flex flex-wrap gap-3">
            <Button href="/rfq/#bulk" size="m" iconStart={<ListPlus aria-hidden size={20} strokeWidth={1.5} />}>
              {t('page.ctaList')}
            </Button>
            <Button href="#request" variant="secondary" size="m">
              {t('page.ctaAsk')}
            </Button>
          </div>
        </PageHeader>

        <section aria-labelledby="sol-tasks" className="mt-14 lg:mt-20">
          <h2 id="sol-tasks" className="text-h3 font-medium text-text">
            {t('page.tasks')}
          </h2>
          <ul className="mt-6 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
            {s.tasks.map((task) => (
              <li key={task} className="flex gap-3 rounded-card bg-surface p-5 text-body text-text">
                <CircleCheck aria-hidden size={22} strokeWidth={1.5} className="mt-0.5 shrink-0 text-accent" />
                {task}
              </li>
            ))}
          </ul>
        </section>

        <section aria-labelledby="sol-groups" className="mt-20 lg:mt-28">
          <h2 id="sol-groups" className={h2}>
            {t('page.groups')}
          </h2>
          <ul className="mt-8 grid gap-4 md:grid-cols-2 xl:grid-cols-3">
            {s.groups.map((g, i) => (
              <li key={g.title} className="flex flex-col rounded-block bg-surface p-6 md:p-8">
                <h3 className="text-h3 font-medium text-text">{g.title}</h3>
                <p className="mt-3 text-body text-text-secondary">{g.text}</p>
                <ul className="mt-5 flex flex-wrap gap-2">
                  {g.links.map((l) => (
                    <li key={l.href}>
                      <Chip label={l.label} href={l.href} />
                    </li>
                  ))}
                </ul>
                {counts[i] ? <p className="mt-auto pt-6 text-small tabular-nums text-text-secondary">{t('page.positions', { count: counts[i] })}</p> : null}
              </li>
            ))}
          </ul>
        </section>

        {products.length ? (
          <section aria-labelledby="sol-featured" className="mt-20 lg:mt-28">
            <div className="flex flex-wrap items-end justify-between gap-4">
              <h2 id="sol-featured" className={h2}>
                {t('page.featured')}
              </h2>
              <Link href="/catalog/" className="inline-flex items-center gap-2 text-body font-semibold text-accent transition-colors hover:text-accent-hover">
                {t('page.allCatalog')}
                <ArrowRight aria-hidden size={18} strokeWidth={1.5} />
              </Link>
            </div>
            <ul className="mt-8 grid grid-cols-1 gap-3 sm:grid-cols-2 md:gap-5 lg:grid-cols-4">
              {products.map((p) => (
                <li key={p.id}>
                  <ProductCard product={p} place="list" />
                </li>
              ))}
            </ul>
          </section>
        ) : null}

        {services.length ? (
          <section aria-labelledby="sol-services" className="mt-20 lg:mt-28">
            <h2 id="sol-services" className={h2}>
              {t('page.services')}
            </h2>
            <ul className="mt-8 flex flex-col gap-2">
              {services.map((x) => (
                <li key={x.slug}>
                  <Link
                    href={`/services/${x.slug}/`}
                    className="group grid gap-2 rounded-block bg-surface px-6 py-6 transition-colors hover:bg-surface-strong md:grid-cols-[minmax(0,5fr)_minmax(0,6fr)_auto] md:items-center md:gap-10 md:px-10 md:py-8"
                  >
                    <h3 className="text-h3 font-medium text-text transition-colors group-hover:text-accent">{x.h1}</h3>
                    <p className="text-body text-text-secondary md:text-lg">{x.summary}</p>
                    <ArrowRight aria-hidden size={24} strokeWidth={1.5} className="hidden text-accent transition-transform group-hover:translate-x-1 md:block" />
                  </Link>
                </li>
              ))}
            </ul>
          </section>
        ) : null}

        {articles.length ? (
          <section aria-labelledby="sol-articles" className="mt-20 lg:mt-28">
            <h2 id="sol-articles" className={h2}>
              {t('page.articles')}
            </h2>
            <ul className="mt-8 grid gap-4 md:grid-cols-2 lg:grid-cols-3">
              {articles.map((a) => (
                <li key={a.slug}>
                  <Link href={`/articles/${a.slug}/`} className="group flex h-full flex-col gap-3 rounded-block bg-surface p-6 transition-colors hover:bg-surface-strong md:p-8">
                    <h3 className="text-h4 font-medium text-text transition-colors group-hover:text-accent">{a.h1}</h3>
                    <p className="line-clamp-3 text-body text-text-secondary">{a.lead}</p>
                    <p className="mt-auto pt-2 text-small text-text-secondary">{t('page.readingTime', { minutes: a.readingMinutes })}</p>
                  </Link>
                </li>
              ))}
            </ul>
          </section>
        ) : null}

        {s.faq?.length ? <FaqSection id="sol-faq" title={t('page.faq')} items={s.faq} className="mt-20 lg:mt-28" /> : null}

        <RequestBlock
          className="mt-20 lg:mt-28"
          title={t('page.requestTitle')}
          text={t('page.requestText')}
          docs={settings.docs}
          defaultMessage={t('page.requestMessage', { name: s.name })}
          formType="solution_request"
        />
      </Container>
    </>
  );
}
