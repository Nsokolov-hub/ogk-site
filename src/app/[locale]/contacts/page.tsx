import type { Metadata } from 'next';
import { Clock, Mail, MapPin, Phone } from 'lucide-react';
import { getTranslations, setRequestLocale } from 'next-intl/server';
import type { Locale } from '@/i18n/routing';
import type { BreadcrumbItem } from '@/types/content';
import { PageHeader } from '@/components/content/PageHeader';
import { RequestBlock } from '@/components/content/RequestBlock';
import { Requisites } from '@/components/content/Requisites';
import { TrackedLink } from '@/components/layout/TrackedLink';
import { breadcrumbsLd, JsonLd, organizationLd } from '@/components/seo/JsonLd';
import { Container } from '@/components/ui/Container';
import { getSiteSettings } from '@/lib/api';
import { contactsPage as page } from '@/data/mock/pages';
import { pageMetadata, SITE_URL } from '@/lib/seo';

type Props = { params: Promise<{ locale: Locale }> };

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { locale } = await params;
  return pageMetadata({ locale, path: '/contacts/', title: page.title, description: page.description, hasEn: page.hasEn });
}

/**
 * Контакты (ТЗ 2.1, SEO-14): телефон, e-mail, адрес и часы работы — те же, что в подвале,
 * в разметке Organization и в карточке Яндекс Бизнеса.
 */
export default async function ContactsPage({ params }: Props) {
  const { locale } = await params;
  setRequestLocale(locale);
  const t = await getTranslations('trust');
  const tc = await getTranslations('catalog');
  const settings = await getSiteSettings();
  const breadcrumbs: BreadcrumbItem[] = [{ label: tc('home'), href: '/' }, { label: page.h1 }];
  const mapHref = `https://yandex.ru/maps/?text=${encodeURIComponent(settings.address.full)}`;
  const big = 'text-h3 font-medium text-text transition-colors hover:text-accent';

  return (
    <>
      <JsonLd data={[breadcrumbsLd(breadcrumbs, SITE_URL, locale, '/contacts/'), organizationLd(settings)]} />
      <Container>
        <PageHeader breadcrumbs={breadcrumbs} title={page.h1} lead={page.lead} size="h1" />

        <div className="mt-14 grid gap-3 md:grid-cols-2 md:gap-4 lg:mt-20">
          <div className="flex flex-col gap-4 rounded-block bg-surface p-6 md:p-10">
            <h2 className="flex items-center gap-3 text-body text-text-secondary">
              <Phone aria-hidden size={20} strokeWidth={1.5} className="text-accent" />
              {t('contacts.phone')}
            </h2>
            <TrackedLink href={settings.phone.href} event="click_phone" params={{ place: 'contacts' }} className={`${big} whitespace-nowrap`}>
              {settings.phone.display}
            </TrackedLink>
          </div>
          <div className="flex flex-col gap-4 rounded-block bg-surface p-6 md:p-10">
            <h2 className="flex items-center gap-3 text-body text-text-secondary">
              <Mail aria-hidden size={20} strokeWidth={1.5} className="text-accent" />
              {t('contacts.email')}
            </h2>
            <div className="flex flex-col gap-2">
              <p>
                <TrackedLink href={`mailto:${settings.emails.order}`} event="click_email" params={{ place: 'contacts' }} className={`${big} break-all`}>
                  {settings.emails.order}
                </TrackedLink>
                <span className="mt-1 block text-small text-text-secondary">{t('contacts.orderEmail')}</span>
              </p>
              <p className="mt-2">
                <TrackedLink href={`mailto:${settings.emails.info}`} event="click_email" params={{ place: 'contacts' }} className="break-all text-h4 font-medium text-text transition-colors hover:text-accent">
                  {settings.emails.info}
                </TrackedLink>
                <span className="mt-1 block text-small text-text-secondary">{t('contacts.infoEmail')}</span>
              </p>
            </div>
          </div>
          <div className="flex flex-col gap-4 rounded-block bg-surface p-6 md:p-10">
            <h2 className="flex items-center gap-3 text-body text-text-secondary">
              <MapPin aria-hidden size={20} strokeWidth={1.5} className="text-accent" />
              {t('contacts.address')}
            </h2>
            <address className="text-h4 font-medium not-italic text-text">{settings.address.full}</address>
            <a href={mapHref} target="_blank" rel="noopener noreferrer" className="w-fit text-body font-medium text-accent underline-offset-2 hover:underline">
              {t('contacts.map')}
              <span className="sr-only"> {t('newTab')}</span>
            </a>
          </div>
          <div className="flex flex-col gap-4 rounded-block bg-surface p-6 md:p-10">
            <h2 className="flex items-center gap-3 text-body text-text-secondary">
              <Clock aria-hidden size={20} strokeWidth={1.5} className="text-accent" />
              {t('contacts.hours')}
            </h2>
            <p className="text-h4 font-medium text-text">{settings.hours}</p>
            <p className="text-body text-text-secondary">{t('contacts.hoursNote')}</p>
          </div>
        </div>

        <div className="mt-20 flex flex-col gap-20 lg:mt-28 lg:gap-28">
          <section aria-labelledby="contacts-requisites" className="grid gap-8 lg:grid-cols-[minmax(0,4fr)_minmax(0,7fr)] lg:gap-16">
            <h2 id="contacts-requisites" className="text-h3 font-medium text-text">
              {t('requisites.title')}
            </h2>
            <Requisites settings={settings} />
          </section>
          <RequestBlock title={t('contacts.formTitle')} text={t('contacts.formText')} docs={settings.docs} formType="contacts_request" />
        </div>
      </Container>
    </>
  );
}
