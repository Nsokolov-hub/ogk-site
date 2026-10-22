export interface SiteSettings {
  siteUrl: string;
  phone: { display: string; href: string };
  emails: { info: string; order: string };
  /** mapQuery — адрес для ссылки на карту, всегда по-русски */
  address: { postalCode: string; city: string; street: string; full: string; mapQuery: string };
  hours: string;
  legal: { name: string; shortName: string; inn: string; kpp: string; ogrn: string };
  docs: { consent: string; privacy: string; card: string };
}
