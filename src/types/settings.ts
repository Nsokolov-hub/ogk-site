export interface SiteSettings {
  siteUrl: string;
  phone: { display: string; href: string };
  emails: { info: string; order: string };
  address: { postalCode: string; city: string; street: string; full: string };
  hours: string;
  legal: { name: string; shortName: string; inn: string; kpp: string; ogrn: string };
  docs: { consent: string; privacy: string; card: string };
}
