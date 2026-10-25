import type { SiteSettings } from '@/types/settings';

/** Контакты и реквизиты — в будущем из админки (ADM-10), один источник для шапки, подвала и Organization */
export const siteSettings: SiteSettings = {
  siteUrl: 'https://www.ogk-chem.ru',
  phone: { display: '+7 495 234 28 63', href: 'tel:+74952342863' },
  emails: { info: 'info@ogk-chem.ru', order: 'order@ogk-chem.ru' },
  address: {
    postalCode: '129301',
    city: 'Москва',
    street: 'ул. Касаткина, д. 8, помещ. 1/1',
    full: '129301, Москва, ул. Касаткина, д. 8, помещ. 1/1',
    mapQuery: '129301, Москва, ул. Касаткина, д. 8',
  },
  hours: 'пн–пт 9:00–18:00',
  legal: {
    name: 'ООО «ОГК-ХИМ»',
    shortName: 'ОГК-ХИМ',
    inn: '9717188828',
    kpp: '771701001',
    ogrn: '1267700023997',
  },
  docs: {
    consent: '/files/soglasie.pdf',
    privacy: '/files/politika.pdf',
    card: '/files/kartochka.pdf',
  },
};

/** Поля контактов на английском (EN-04): адрес, часы работы, название организации */
export const siteSettingsEn: SiteSettings = {
  ...siteSettings,
  address: {
    ...siteSettings.address,
    city: 'Moscow',
    street: '8 Kasatkina St., premises 1/1',
    full: '8 Kasatkina St., premises 1/1, Moscow 129301, Russia',
  },
  hours: 'Mon–Fri 9:00–18:00 (Moscow time)',
  legal: { ...siteSettings.legal, name: 'OGK-CHEM LLC', shortName: 'OGK-CHEM' },
};
