import type { SiteSettings } from '@/types/settings';

/** Структурированные данные (ТЗ SEO-06). Экранируем «<», чтобы JSON не закрыл тег script. */
export function JsonLd({ data }: { data: Record<string, unknown> | Record<string, unknown>[] }) {
  return (
    <script
      type="application/ld+json"
      dangerouslySetInnerHTML={{ __html: JSON.stringify(data).replace(/</g, '\\u003c') }}
    />
  );
}

export function organizationLd(s: SiteSettings) {
  return {
    '@context': 'https://schema.org',
    '@type': 'Organization',
    '@id': `${s.siteUrl}/#organization`,
    name: s.legal.shortName,
    legalName: s.legal.name,
    url: `${s.siteUrl}/`,
    logo: `${s.siteUrl}/images/brand/logo.svg`,
    email: s.emails.info,
    telephone: s.phone.href.replace('tel:', ''),
    taxID: s.legal.inn,
    address: {
      '@type': 'PostalAddress',
      postalCode: s.address.postalCode,
      addressLocality: s.address.city,
      streetAddress: s.address.street,
      addressCountry: 'RU',
    },
    contactPoint: {
      '@type': 'ContactPoint',
      telephone: s.phone.href.replace('tel:', ''),
      email: s.emails.order,
      contactType: 'sales',
      availableLanguage: ['Russian', 'English'],
      hoursAvailable: {
        '@type': 'OpeningHoursSpecification',
        dayOfWeek: ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday'],
        opens: '09:00',
        closes: '18:00',
      },
    },
  };
}

/** BreadcrumbList: у последнего звена ссылки нет — подставляем адрес текущей страницы */
export function breadcrumbsLd(items: { label: string; href?: string }[], siteUrl: string, locale: string, currentHref: string) {
  const abs = (href: string) => `${siteUrl}${locale === 'ru' ? '' : `/${locale}`}${href}`;
  return {
    '@context': 'https://schema.org',
    '@type': 'BreadcrumbList',
    itemListElement: items.map((item, i) => ({
      '@type': 'ListItem',
      position: i + 1,
      name: item.label,
      item: abs(item.href ?? currentHref),
    })),
  };
}

/** FAQPage — только там, где вопросы видны на странице (ТЗ SEO-06) */
export function faqLd(faq: { q: string; a: string }[]) {
  return {
    '@context': 'https://schema.org',
    '@type': 'FAQPage',
    mainEntity: faq.map((f) => ({
      '@type': 'Question',
      name: f.q,
      acceptedAnswer: { '@type': 'Answer', text: f.a },
    })),
  };
}

export function websiteLd(s: SiteSettings, locale: string) {
  const base = locale === 'ru' ? s.siteUrl : `${s.siteUrl}/${locale}`;
  return {
    '@context': 'https://schema.org',
    '@type': 'WebSite',
    '@id': `${s.siteUrl}/#website`,
    url: `${base}/`,
    name: s.legal.shortName,
    inLanguage: locale,
    publisher: { '@id': `${s.siteUrl}/#organization` },
    potentialAction: {
      '@type': 'SearchAction',
      target: { '@type': 'EntryPoint', urlTemplate: `${base}/search/?q={search_term_string}` },
      'query-input': 'required name=search_term_string',
    },
  };
}
