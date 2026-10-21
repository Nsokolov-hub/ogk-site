import type { Metadata } from 'next';
import { getTranslations, setRequestLocale } from 'next-intl/server';
import type { Locale } from '@/i18n/routing';
import type { BreadcrumbItem } from '@/types/content';
import { PageHeader } from '@/components/content/PageHeader';
import { breadcrumbsLd, JsonLd } from '@/components/seo/JsonLd';
import { Container } from '@/components/ui/Container';
import { Link } from '@/i18n/navigation';
import { getSubstanceList } from '@/lib/product-api';
import { pageMetadata, SITE_URL } from '@/lib/seo';

type Props = { params: Promise<{ locale: Locale }> };

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { locale } = await params;
  const t = await getTranslations({ locale, namespace: 'substancePage.list' });
  return pageMetadata({ locale, path: '/substances/', title: t('title'), description: t('description') });
}

/** Указатель субстанций А–Я: вход в страницы «стандарты и примеси к одному API» (ТЗ 4.1, SC-05) */
export default async function SubstancesIndex({ params }: Props) {
  const { locale } = await params;
  setRequestLocale(locale);
  const t = await getTranslations('substancePage.list');
  const tc = await getTranslations('catalog');
  const list = getSubstanceList().sort((a, b) => a.nameRu.localeCompare(b.nameRu, 'ru'));
  const breadcrumbs: BreadcrumbItem[] = [{ label: tc('home'), href: '/' }, { label: t('breadcrumb') }];

  // Группы по первой букве русского названия
  const groups = new Map<string, typeof list>();
  for (const s of list) {
    const letter = s.nameRu[0].toUpperCase();
    groups.set(letter, [...(groups.get(letter) ?? []), s]);
  }

  return (
    <>
      <JsonLd data={breadcrumbsLd(breadcrumbs, SITE_URL, locale, '/substances/')} />
      <Container>
        <PageHeader breadcrumbs={breadcrumbs} title={t('h1')} lead={t('lead')} />

        <nav aria-label={t('letters')} className="mt-10">
          <ul className="flex flex-wrap gap-2">
            {Array.from(groups.keys()).map((l) => (
              <li key={l}>
                <a href={`#letter-${l}`} className="inline-grid size-11 place-items-center rounded-full bg-surface-strong text-body font-medium text-text transition-colors hover:text-accent">
                  {l}
                </a>
              </li>
            ))}
          </ul>
        </nav>

        <div className="mt-12 columns-1 gap-10 sm:columns-2 lg:columns-3 2xl:columns-4">
          {Array.from(groups.entries()).map(([letter, items]) => (
            <section key={letter} id={`letter-${letter}`} aria-labelledby={`h-${letter}`} className="mb-10 break-inside-avoid scroll-mt-32">
              <h2 id={`h-${letter}`} className="text-h3 font-medium text-accent">
                {letter}
              </h2>
              <ul className="mt-3 flex flex-col gap-1">
                {items.map((s) => (
                  <li key={s.slug}>
                    <Link href={`/substances/${s.slug}/`} className="group flex items-baseline justify-between gap-4 rounded-sm py-1.5 text-body text-text transition-colors hover:text-accent">
                      <span>
                        {s.nameRu} <span className="text-small text-text-secondary group-hover:text-accent">{s.nameEn}</span>
                      </span>
                      <span className="shrink-0 text-small tabular-nums text-text-secondary">{s.count}</span>
                    </Link>
                  </li>
                ))}
              </ul>
            </section>
          ))}
        </div>
      </Container>
    </>
  );
}
