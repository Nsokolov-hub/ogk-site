import type { Metadata } from 'next';
import Image from 'next/image';
import { notFound } from 'next/navigation';
import { CircleCheck, Phone } from 'lucide-react';
import { getTranslations, setRequestLocale } from 'next-intl/server';
import type { Locale } from '@/i18n/routing';
import type { BreadcrumbItem } from '@/types/content';
import { FaqSection } from '@/components/content/FaqSection';
import { LinkChips } from '@/components/content/LinkChips';
import { PageHeader } from '@/components/content/PageHeader';
import { ServiceRequestForm } from '@/components/forms/ServiceRequestForm';
import { TrackedLink } from '@/components/layout/TrackedLink';
import { breadcrumbsLd, faqLd, JsonLd, serviceLd } from '@/components/seo/JsonLd';
import { TrackView } from '@/components/seo/TrackView';
import { Button } from '@/components/ui/Button';
import { Chip } from '@/components/ui/Chip';
import { Container } from '@/components/ui/Container';
import { Icon } from '@/components/ui/Icon';
import { getSiteSettings } from '@/lib/api';
import { getService, getServices } from '@/lib/content-api';
import { absoluteUrl, pageMetadata, SITE_URL } from '@/lib/seo';

type Props = { params: Promise<{ locale: Locale; slug: string }> };

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { locale, slug } = await params;
  const s = await getService(slug, locale);
  if (!s) return {};
  return pageMetadata({ locale, path: `/services/${s.slug}/`, title: s.title, description: s.description, hasEn: s.hasEn });
}

export default async function ServicePage({ params }: Props) {
  const { locale, slug } = await params;
  setRequestLocale(locale);
  const [s, all, settings] = await Promise.all([getService(slug, locale), getServices(locale), getSiteSettings(locale)]);
  if (!s) notFound();
  const t = await getTranslations('services');
  const tc = await getTranslations('catalog');
  const path = `/services/${s.slug}/`;

  const breadcrumbs: BreadcrumbItem[] = [
    { label: tc('home'), href: '/' },
    { label: t('list.breadcrumb'), href: '/services/' },
    { label: s.name },
  ];
  const ld: Record<string, unknown>[] = [
    breadcrumbsLd(breadcrumbs, SITE_URL, locale, path),
    serviceLd({ url: absoluteUrl(locale, path), name: s.h1, description: s.description, siteUrl: SITE_URL }),
  ];
  if (s.faq?.length) ld.push(faqLd(s.faq));

  const others = all.filter((x) => x.slug !== s.slug).map((x) => ({ label: x.name, href: `/services/${x.slug}/` }));
  const h2 = 'text-h3 font-medium text-text';

  return (
    <>
      <JsonLd data={ld} />
      <TrackView event="service_view" params={{ service: s.slug }} />
      <Container>
        <div className="grid gap-10 lg:grid-cols-[minmax(0,7fr)_minmax(0,4fr)] lg:items-end lg:gap-16">
          <PageHeader breadcrumbs={breadcrumbs} title={s.h1} lead={s.intro} size="h1">
            <div className="mt-8 flex flex-wrap items-center gap-3">
              <Button href="#service-form" size="m">
                {s.form.title}
              </Button>
              <TrackedLink
                href={settings.phone.href}
                event="click_phone"
                params={{ place: 'service' }}
                className="inline-flex h-12 items-center gap-2 rounded-pill bg-surface-strong px-[22px] text-body font-semibold text-accent transition-colors hover:text-accent-hover sm:text-lg"
              >
                <Phone aria-hidden size={18} strokeWidth={1.5} />
                {settings.phone.display}
              </TrackedLink>
            </div>
          </PageHeader>
          {s.image ? (
            <div className="relative hidden aspect-[4/3] overflow-hidden rounded-block bg-surface lg:block">
              <Image src={s.image.src} alt={s.image.alt} fill priority sizes="(min-width: 1024px) 33vw, 0px" className="object-contain p-8" />
            </div>
          ) : null}
        </div>

        <div className="mt-20 flex flex-col gap-20 lg:mt-28 lg:gap-28">
          {/* Что входит */}
          <section aria-labelledby="service-includes">
            <h2 id="service-includes" className={h2}>
              {t('page.includes')}
            </h2>
            <ul className="mt-8 grid gap-x-12 gap-y-5 md:grid-cols-2">
              {s.includes.map((item) => (
                <li key={item} className="flex gap-3 text-body text-text md:text-lg">
                  <CircleCheck aria-hidden size={24} strokeWidth={1.5} className="mt-0.5 shrink-0 text-accent" />
                  {item}
                </li>
              ))}
            </ul>
          </section>

          {/* Как работаем — настоящая последовательность, поэтому нумерованный список */}
          <section aria-labelledby="service-steps">
            <h2 id="service-steps" className={h2}>
              {t('page.steps')}
            </h2>
            <ol className="mt-8 grid gap-3 sm:grid-cols-2 lg:grid-cols-[repeat(auto-fit,minmax(200px,1fr))]">
              {s.steps.map((step, i) => (
                <li key={step.title} className="flex flex-col gap-3 rounded-block bg-surface p-6 md:p-7">
                  <span aria-hidden className="text-h2 font-medium leading-none text-accent">
                    {i + 1}
                  </span>
                  <h3 className="text-h4 font-medium text-text">{step.title}</h3>
                  <p className="text-body text-text-secondary">{step.text}</p>
                </li>
              ))}
            </ol>
          </section>

          {s.table ? (
            <section aria-labelledby="service-table">
              <h2 id="service-table" className={h2}>
                {s.table.caption}
              </h2>
              <div className="mt-8 overflow-x-auto rounded-block">
                <table className="w-full min-w-[640px] border-collapse text-left">
                  <caption className="sr-only">{s.table.caption}</caption>
                  <thead className="bg-surface-strong">
                    <tr>
                      {s.table.head.map((h) => (
                        <th key={h} scope="col" className="px-5 py-4 text-small font-medium text-text-secondary">
                          {h}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {s.table.rows.map((row, i) => (
                      <tr key={row[0]} className={i % 2 === 0 ? 'bg-surface' : undefined}>
                        {row.map((cell, j) =>
                          j === 0 ? (
                            <th key={cell} scope="row" className="whitespace-nowrap px-5 py-4 text-body font-medium text-accent">
                              {cell}
                            </th>
                          ) : (
                            <td key={cell} className="px-5 py-4 text-body text-text">
                              {cell}
                            </td>
                          ),
                        )}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </section>
          ) : null}

          {s.countries?.length ? (
            <section aria-labelledby="service-countries">
              <h2 id="service-countries" className={h2}>
                {t('page.countries', { count: s.countries.length })}
              </h2>
              <ul className="mt-8 flex flex-wrap gap-2">
                {s.countries.map((c) => (
                  <li key={c}>
                    <Chip label={c} />
                  </li>
                ))}
              </ul>
            </section>
          ) : null}

          {s.needs?.length ? (
            <section aria-labelledby="service-needs" className="max-w-[880px]">
              <h2 id="service-needs" className={h2}>
                {t('page.needs')}
              </h2>
              <ul className="mt-8 flex flex-col gap-3">
                {s.needs.map((n) => (
                  <li key={n} className="rounded-field bg-surface px-5 py-4 text-body text-text md:text-lg">
                    {n}
                  </li>
                ))}
              </ul>
            </section>
          ) : null}

          {/* Форма расчёта (SC-06) */}
          <section id="service-form" aria-labelledby="service-form-title" className="scroll-mt-28 rounded-block bg-surface p-6 md:p-10 lg:p-14">
            <div className="grid gap-10 lg:grid-cols-[minmax(0,4fr)_minmax(0,7fr)] lg:gap-16">
              <div>
                <h2 id="service-form-title" className={h2}>
                  {s.form.title}
                </h2>
                <p className="mt-4 text-body text-text-secondary md:text-lg">{s.form.text}</p>
                <ul className="mt-8 hidden flex-col gap-5 lg:flex">
                  {(['zap', 'user', 'mail'] as const).map((icon) => (
                    <li key={icon} className="flex gap-4">
                      <span className="grid size-11 shrink-0 place-items-center rounded-full bg-surface-strong">
                        <Icon name={icon} size={20} />
                      </span>
                      <span className="text-body text-text">{t(`page.promises.${icon}`)}</span>
                    </li>
                  ))}
                </ul>
              </div>
              <ServiceRequestForm service={{ slug: s.slug, name: s.h1 }} fieldKinds={s.form.fields} docs={settings.docs} />
            </div>
          </section>

          {s.faq?.length ? <FaqSection id="service-faq" title={t('page.faq')} items={s.faq} /> : null}

          <LinkChips id="service-related" title={t('page.related')} items={[...s.related, ...others.filter((o) => !s.related.some((r) => r.href === o.href))]} />
        </div>
      </Container>
    </>
  );
}
