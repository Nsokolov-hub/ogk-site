import Image from 'next/image';
import { ChevronDown, CircleCheck, FileText } from 'lucide-react';
import { getTranslations } from 'next-intl/server';
import type { CategoryPageData } from '@/types/content';
import type { SiteSettings } from '@/types/settings';
import { RequestForm } from '@/components/forms/RequestForm';
import { Chip } from '@/components/ui/Chip';
import { Link } from '@/i18n/navigation';

/**
 * Блоки под сеткой (ТЗ 5.5): производители → полезная информация → условия поставки → документы → FAQ →
 * внутренние ссылки → форма заявки.
 */
export async function CategorySections({ data, docs }: { data: CategoryPageData; docs: SiteSettings['docs'] }) {
  const t = await getTranslations('catalog.sections');
  const { content, brands } = data;
  const h2 = 'text-h3 font-medium text-text';

  return (
    <div className="mt-24 flex flex-col gap-20 md:mt-32 lg:gap-28">
      {brands.length ? (
        <section aria-labelledby="cat-brands">
          <h2 id="cat-brands" className={h2}>
            {t('brands')}
          </h2>
          <ul className="mt-6 grid grid-cols-2 gap-3 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6">
            {brands.map((b) => (
              <li key={b.slug}>
                <Link
                  href={`/brands/${b.slug}/`}
                  className="flex h-32 flex-col items-center justify-center gap-1 overflow-hidden rounded-card bg-surface p-3 text-center transition-colors hover:bg-surface-strong"
                >
                  {b.logo ? (
                    <Image src={b.logo} alt={b.name} width={212} height={172} unoptimized className="h-20 w-auto object-contain" />
                  ) : (
                    <span className="text-body font-medium text-text">{b.name}</span>
                  )}
                  <span className="text-caption text-text-secondary">{t('brandCount', { count: b.count })}</span>
                </Link>
              </li>
            ))}
          </ul>
        </section>
      ) : null}

      {content.seoText?.length ? (
        <section aria-labelledby="cat-info" className="max-w-[72ch]">
          <h2 id="cat-info" className={h2}>
            {t('info')}
          </h2>
          <div className="mt-6 flex flex-col gap-4 text-body text-text md:text-lg">
            {content.seoText.map((p) => (
              <p key={p.slice(0, 24)}>{p}</p>
            ))}
          </div>
        </section>
      ) : null}

      <div className="grid gap-16 lg:grid-cols-2 lg:gap-12">
        {content.delivery?.length ? (
          <section aria-labelledby="cat-delivery">
            <h2 id="cat-delivery" className={h2}>
              {t('delivery')}
            </h2>
            <ul className="mt-6 flex flex-col gap-4">
              {content.delivery.map((d) => (
                <li key={d} className="flex gap-3 text-body text-text">
                  <CircleCheck aria-hidden size={22} strokeWidth={1.5} className="mt-0.5 shrink-0 text-accent" />
                  {d}
                </li>
              ))}
            </ul>
          </section>
        ) : null}

        {content.documents?.length ? (
          <section aria-labelledby="cat-docs">
            <h2 id="cat-docs" className={h2}>
              {t('documents')}
            </h2>
            <ul className="mt-6 flex flex-col gap-3">
              {content.documents.map((d) => (
                <li key={d.href}>
                  <a
                    href={d.href}
                    target="_blank"
                    rel="noopener"
                    className="flex items-center gap-3 rounded-field bg-surface px-5 py-4 text-body text-text transition-colors hover:bg-surface-strong hover:text-accent"
                  >
                    <FileText aria-hidden size={22} strokeWidth={1.5} className="shrink-0 text-accent" />
                    {d.title}
                    <span className="sr-only"> {t('newTab')}</span>
                  </a>
                </li>
              ))}
            </ul>
          </section>
        ) : null}
      </div>

      {content.faq?.length ? (
        <section aria-labelledby="cat-faq" className="max-w-[960px]">
          <h2 id="cat-faq" className={h2}>
            {t('faq')}
          </h2>
          <div className="mt-6 flex flex-col gap-3">
            {content.faq.map((f) => (
              <details key={f.q} className="group rounded-field bg-surface px-5 md:px-6">
                <summary className="flex cursor-pointer list-none items-center justify-between gap-4 py-4 text-body font-medium text-text md:text-lg [&::-webkit-details-marker]:hidden">
                  {f.q}
                  <ChevronDown aria-hidden size={20} strokeWidth={1.5} className="shrink-0 text-accent transition-transform group-open:rotate-180" />
                </summary>
                <p className="pb-5 text-body text-text-secondary">{f.a}</p>
              </details>
            ))}
          </div>
        </section>
      ) : null}

      {content.related?.length ? (
        <section aria-labelledby="cat-related">
          <h2 id="cat-related" className={h2}>
            {t('related')}
          </h2>
          <ul className="mt-6 flex flex-wrap gap-2">
            {content.related.map((r) => (
              <li key={r.href}>
                <Chip label={r.label} href={r.href} />
              </li>
            ))}
          </ul>
        </section>
      ) : null}

      <section id="catalog-request" aria-labelledby="cat-request" className="scroll-mt-28 rounded-block bg-surface p-6 md:p-10 lg:p-14">
        <div className="grid gap-10 lg:grid-cols-[minmax(0,5fr)_minmax(0,7fr)] lg:gap-16">
          <div>
            <h2 id="cat-request" className="text-h3 font-medium text-text">
              {t('requestTitle')}
            </h2>
            <p className="mt-4 text-body text-text-secondary md:text-lg">{t('requestText')}</p>
          </div>
          <RequestForm docs={docs} />
        </div>
      </section>
    </div>
  );
}
