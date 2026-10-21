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

/**
 * Product (SEO-06): name, sku, mpn, brand, image, description.
 * Блока offers нет: цены на витрине не показываются, а offers без price невалиден.
 */
export function productLd(p: {
  url: string;
  name: string;
  sku: string;
  brand: string;
  description: string;
  image?: string;
  cas?: string;
  category?: string;
}) {
  return {
    '@context': 'https://schema.org',
    '@type': 'Product',
    '@id': `${p.url}#product`,
    url: p.url,
    name: p.name,
    sku: p.sku,
    mpn: p.sku,
    brand: { '@type': 'Brand', name: p.brand },
    description: p.description,
    ...(p.image ? { image: p.image } : {}),
    ...(p.category ? { category: p.category } : {}),
    ...(p.cas ? { additionalProperty: [{ '@type': 'PropertyValue', name: 'CAS', value: p.cas }] } : {}),
  };
}

export function articleLd(p: {
  url: string;
  headline: string;
  description: string;
  datePublished: string;
  dateModified: string;
  author: { name: string; url: string; jobTitle?: string };
  siteUrl: string;
  image?: string;
}) {
  return {
    '@context': 'https://schema.org',
    '@type': 'Article',
    '@id': `${p.url}#article`,
    mainEntityOfPage: p.url,
    headline: p.headline,
    description: p.description,
    datePublished: p.datePublished,
    dateModified: p.dateModified,
    inLanguage: 'ru',
    author: { '@type': 'Person', name: p.author.name, url: p.author.url, ...(p.author.jobTitle ? { jobTitle: p.author.jobTitle } : {}) },
    publisher: { '@id': `${p.siteUrl}/#organization` },
    ...(p.image ? { image: p.image } : {}),
  };
}

export function personLd(p: { url: string; name: string; jobTitle: string; siteUrl: string }) {
  return {
    '@context': 'https://schema.org',
    '@type': 'Person',
    '@id': `${p.url}#person`,
    url: p.url,
    name: p.name,
    jobTitle: p.jobTitle,
    worksFor: { '@id': `${p.siteUrl}/#organization` },
  };
}

/** Услуга: кто оказывает и где (дополняет BreadcrumbList и FAQPage на странице услуги) */
export function serviceLd(p: { url: string; name: string; description: string; siteUrl: string }) {
  return {
    '@context': 'https://schema.org',
    '@type': 'Service',
    '@id': `${p.url}#service`,
    url: p.url,
    name: p.name,
    description: p.description,
    provider: { '@id': `${p.siteUrl}/#organization` },
    areaServed: { '@type': 'Country', name: 'RU' },
  };
}
