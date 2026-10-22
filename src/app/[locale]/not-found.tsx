import type { CSSProperties } from 'react';
import Image from 'next/image';
import { getLocale, getTranslations } from 'next-intl/server';
import type { Locale } from '@/i18n/routing';
import { HeaderSearch } from '@/components/layout/HeaderSearch';
import { Button } from '@/components/ui/Button';
import { Container } from '@/components/ui/Container';
import { categoryShortName } from '@/data/mock/categories';
import { getCatalogTree } from '@/lib/api';

/**
 * 404 (ТЗ SEO-05): объясняет, что случилось, и сразу даёт выход — поиск по кат. № и CAS,
 * разделы каталога, главную и заявку. Страница закрыта от индексации.
 */
const enter = (i: number) => ({ '--enter-i': i }) as CSSProperties;

export default async function NotFound() {
  const t = await getTranslations('notFound');
  const locale = (await getLocale()) as Locale;
  const tree = await getCatalogTree(locale);

  return (
    <Container className="grid items-center gap-12 pb-8 pt-28 md:pt-36 lg:min-h-[92svh] lg:grid-cols-[minmax(0,7fr)_minmax(0,5fr)] lg:gap-16 lg:pt-40">
      {/* React 19 поднимает title и meta в head */}
      <title>{`${t('title')} — ОГК-ХИМ`}</title>
      <meta name="robots" content="noindex" />

      <div className="min-w-0">
        <p style={enter(0)} className="enter text-lead text-accent">{t('code')}</p>
        <h1 style={enter(1)} className="enter mt-3 text-h1 font-medium text-text">{t('title')}</h1>
        <p style={enter(2)} className="enter mt-5 text-lead text-text lg:max-w-[60ch]">{t('text')}</p>

        <div style={enter(3)} className="enter mt-8 lg:max-w-[640px]">
          <HeaderSearch />
        </div>

        <h2 style={enter(4)} className="enter mt-10 text-body font-medium text-text-secondary">{t('sections')}</h2>
        <ul style={enter(5)} className="enter mt-3 flex flex-wrap gap-2">
          {tree.map((c) => (
            <li key={c.slug}>
              <Button href={c.href} variant="menu" size="s">
                {categoryShortName(c.slug, locale) ?? c.name}
              </Button>
            </li>
          ))}
        </ul>

        <div style={enter(6)} className="enter mt-10 flex flex-wrap items-center gap-3">
          <Button href="/" size="m">
            {t('home')}
          </Button>
          <Button href="/rfq/" variant="secondary" size="m">
            {t('requestAction')}
          </Button>
        </div>
        <p style={enter(7)} className="enter mt-4 text-small text-text-secondary lg:max-w-[60ch]">{t('request')}</p>
      </div>

      <div aria-hidden style={enter(2)} className="enter relative mx-auto hidden aspect-[824/1478] w-full max-w-[500px] lg:block">
        <Image src="/images/home/hero-2.png" alt="" fill sizes="500px" className="object-contain" />
      </div>
    </Container>
  );
}
