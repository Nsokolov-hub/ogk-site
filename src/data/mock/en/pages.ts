import type { aboutPage, contactsPage, deliveryPage, documentsPage } from '../pages';

/** Страницы доверия на английском (EN-04). Только факты, как в русской версии */

const D = '2026-10-22';

export const aboutPageEn: typeof aboutPage = {
  h1: 'About OGK-CHEM',
  title: 'About OGK-CHEM — supplies for pharmaceutical laboratories',
  description:
    'OGK-CHEM supplies pharmaceutical laboratories with reference standards, reagents, HPLC consumables and equipment from 60+ manufacturers, and organises cold chain logistics and customs clearance.',
  lead: 'OGK-CHEM is a specialised company that provides pharmaceutical manufacturers with everything they need for accurate laboratory research and development. We help optimise procurement and guarantee the quality of supplied products.',
  facts: [
    { value: '60+', label: 'global manufacturers' },
    { value: '23', label: 'countries we deliver from' },
    { value: '2 hours', label: 'to reply to a request during business hours' },
  ],
  directions: [
    { title: 'Reference standards', text: 'EDQM, USP and British Pharmacopoeia standards, secondary standards and impurity standards.', href: '/catalog/reference-standards/' },
    { title: 'Reagents and chromatography', text: 'HPLC and LC-MS solvents, columns, guard columns, filters and fittings.', href: '/catalog/chromatography/' },
    { title: 'Logistics and cold chain', text: 'Delivery from 23 countries with temperature control: insulated shippers, coolant packs, data loggers.', href: '/services/cold-chain/' },
    { title: 'Customs and permits', text: 'HS codes, customs clearance, Ministry of Health and FSTEC import permits.', href: '/services/customs-clearance/' },
  ],
  steps: [
    { title: 'Request', text: 'You send a quote cart, a list of items or a description of the task.' },
    { title: 'Calculation', text: 'Within 2 business hours a manager clarifies the details and contacts manufacturers.' },
    { title: 'Quotation', text: 'We send the price, lead time and terms for each item.' },
    { title: 'Supply', text: 'We purchase, deliver under the required storage conditions and clear customs.' },
    { title: 'Documents', text: 'We hand over the goods with manufacturer documents and closing documents.' },
  ],
  audience: [
    { title: 'Analytical chemists and QC', text: 'Items by catalogue number or CAS, purity, storage conditions and documents.' },
    { title: 'Laboratory and R&D managers', text: 'Standards and impurities for a substance, columns for a method.' },
    { title: 'Procurement', text: 'One quotation for a list, lead times, company details and documents for public procurement.' },
    { title: 'Foreign trade specialists', text: 'Cold chain, customs, HS codes and import permits.' },
  ],
  hasEn: true,
  updatedAt: D,
};

export const deliveryPageEn: typeof deliveryPage = {
  h1: 'Delivery and supply terms',
  title: 'Delivery and supply terms for laboratory materials | OGK-CHEM',
  description:
    'How we supply reference standards, reagents and equipment: delivery across Russia and from 23 countries, temperature ranges, lead times, payment by invoice and documents for public procurement.',
  lead: 'We supply to order from manufacturer catalogues and deliver to any region of Russia under the required storage conditions. The price, lead time and terms for each item are stated in the quotation.',
  sections: [
    {
      id: 'geo',
      title: 'Geography',
      text: 'We deliver to any region of Russia, to your warehouse or laboratory. We purchase from manufacturers and distributors in 23 countries in the Americas, Europe, Asia and the CIS.',
    },
    {
      id: 'terms',
      title: 'Lead times',
      text: 'The lead time depends on the manufacturer, its stock, the route and any permits required. We state it for each item in the quotation and let you know if anything changes.',
    },
    {
      id: 'temperature',
      title: 'Storage conditions in transit',
      items: [
        'Room temperature +15…+25 °C',
        'Cold chain +2…+8 °C — insulated shipper with coolant packs',
        'Frozen −20 °C and dry ice for deep-frozen cargo',
        'Temperature logger and trip report on request',
      ],
    },
    {
      id: 'payment',
      title: 'Payment',
      text: 'We work with legal entities by bank transfer: we issue an invoice once the quotation is agreed. Payment terms are set out in the contract.',
    },
    {
      id: 'documents',
      title: 'Documents with the delivery',
      items: [
        'Manufacturer documents: certificate of analysis (CoA), safety data sheet (SDS), leaflet',
        'Closing documents for accounting',
        'For public procurement under 44-FZ and 223-FZ — quotations and specifications in your format',
      ],
    },
  ],
  faq: [
    { q: 'Can I find out the lead time before ordering?', a: 'Yes, we state the lead time for each item in the quotation — before the invoice is issued.' },
    { q: 'Do you deliver to the regions?', a: 'Yes, to any region of Russia, including under cold chain conditions.' },
    { q: 'Do you work with public procurement?', a: 'Yes. We will prepare quotations and documents for procurement under 44-FZ and 223-FZ.' },
  ],
  links: [
    { label: 'Cold chain', href: '/services/cold-chain/' },
    { label: 'Customs clearance', href: '/services/customs-clearance/' },
    { label: 'Documents', href: '/documents/' },
    { label: 'Contacts', href: '/contacts/' },
  ],
  hasEn: true,
  updatedAt: D,
};

export const documentsPageEn: typeof documentsPage = {
  h1: 'Documents',
  title: 'Documents and company details of OGK-CHEM LLC',
  description:
    'Company details of OGK-CHEM LLC, company profile, privacy policy, consent to personal data processing and documents accompanying supplies.',
  lead: 'Company details and legal documents of OGK-CHEM LLC, as well as the documents that accompany a supply. We will send samples of accompanying documents on request.',
  supplyDocs: [
    { title: 'Certificate of analysis (CoA)', text: 'Confirms the identity and quality parameters of the batch. A CoA for a specific batch is available on request.' },
    { title: 'Safety data sheet (SDS)', text: 'Properties of the substance, safety measures, storage and transport conditions.' },
    { title: 'Manufacturer leaflet', text: 'For pharmacopoeial standards: conditions of use and storage.' },
    { title: 'Strain product sheet', text: 'For microorganisms: rehydration and cultivation conditions.' },
    { title: 'Certificates and manuals', text: 'For columns and equipment: manufacturer certificate and user manual.' },
    { title: 'Permits', text: 'Import permits, if they were required for the supply.' },
  ],
  edo: 'We work with electronic document interchange (EDI). Your manager will provide the operator and participant ID.',
  licenses: 'Copies of licences, certificates and manufacturer distribution letters are available on request.',
  hasEn: true,
  updatedAt: D,
};

export const contactsPageEn: typeof contactsPage = {
  h1: 'Contacts',
  title: 'Contact OGK-CHEM — phone, address, company details',
  description:
    'OGK-CHEM contacts: +7 495 234 28 63, info@ogk-chem.ru, order@ogk-chem.ru. 8 Kasatkina St., Moscow. Mon–Fri 9:00–18:00 Moscow time. Company details of OGK-CHEM LLC.',
  lead: 'Call, write or send a request through the form — we reply within 2 business hours.',
  hasEn: true,
  updatedAt: D,
};
