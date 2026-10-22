import type { ServiceContent } from '@/types/content';
import { services } from '../services';

/**
 * Услуги на английском (EN-04). Поля формы, картинки и даты — из русской версии; здесь только тексты.
 */

export const COUNTRIES_EN = [
  'USA', 'Canada', 'United Kingdom', 'France', 'Sweden', 'Germany', 'Norway', 'China', 'Armenia', 'Georgia',
  'Netherlands', 'Switzerland', 'Russia', 'Kazakhstan', 'Uzbekistan', 'Azerbaijan', 'Austria', 'Belgium', 'Australia',
  'Japan', 'South Korea', 'Italy', 'Spain',
];

type Text = Omit<ServiceContent, 'slug' | 'form' | 'image' | 'updatedAt' | 'countries'> & {
  form: { title: string; text: string };
  imageAlt?: string;
};

const en: Record<string, Text> = {
  'research-drug-supply': {
    name: 'Supply of medicines for research',
    h1: 'Supply of medicinal products for research',
    title: 'Supply of medicinal products to Russia for research purposes | OGK-CHEM',
    description:
      'We supply medicinal products to Russia for research and laboratory testing: selection, purchase from the manufacturer, import permit, cold chain and customs. Reply within 2 business hours.',
    summary: 'Selection, purchase and import of medicines, including those not registered in Russia, with an import permit.',
    intro:
      'We supply medicinal products for research and laboratory testing, including products not registered in Russia. We select the product, buy it from the manufacturer or distributor, obtain the import permit and deliver under the required storage conditions.',
    includes: [
      'Product selection by INN or trade name, manufacturer, dosage form and strength',
      'Purchase from the manufacturer or an authorised distributor in the country of origin',
      'Ministry of Health of Russia import permit if the product is not registered in Russia',
      'Temperature-controlled delivery: +15…+25 °C, +2…+8 °C, −20 °C',
      'Customs clearance and manufacturer accompanying documents',
      'Reference medicinal products for comparative testing',
    ],
    steps: [
      { title: 'Request', text: 'Send the INN or trade name, manufacturer, dosage form, strength, quantity and purpose of import.' },
      { title: 'Selection and quote', text: 'We check availability with manufacturers, lead times and required permits, then send a quotation.' },
      { title: 'Documents', text: 'We prepare the document package and obtain the import permit if required.' },
      { title: 'Purchase and delivery', text: 'We buy the batch, deliver it with temperature control and clear customs.' },
      { title: 'Handover', text: 'We deliver to your warehouse or laboratory with the accompanying documents.' },
    ],
    needs: [
      'INN or trade name, manufacturer',
      'Dosage form, strength, number of packs',
      'Purpose of import and receiving organisation',
      'Desired delivery date',
    ],
    faq: [
      {
        q: 'Can a product not registered in Russia be imported?',
        a: 'For research purposes, yes — under a Ministry of Health of Russia permit for the specific batch. We will help prepare the documents; the timing depends on the product and the completeness of the package.',
      },
      {
        q: 'Do you supply reference products for comparative testing?',
        a: 'Yes. Reference medicinal products are in a separate catalogue section; if you can’t find what you need, send us a request.',
      },
    ],
    related: [
      { label: 'Reference medicinal products', href: '/catalog/reference-drugs/' },
      { label: 'Import permits', href: '/services/import-permits/' },
      { label: 'Cold chain', href: '/services/cold-chain/' },
      { label: 'Customs clearance', href: '/services/customs-clearance/' },
    ],
    form: {
      title: 'Request a supply of medicines',
      text: 'Describe the products and quantities — we will check availability and send a quotation within 2 business hours.',
    },
    imageAlt: 'Medicine vial',
  },
  'pharma-logistics': {
    name: 'Pharmaceutical logistics',
    h1: 'Pharmaceutical cargo logistics',
    title: 'Pharmaceutical logistics and cargo delivery | OGK-CHEM',
    description:
      'Delivery of pharmaceutical cargo, reference standards and laboratory materials from 23 countries and within Russia: transport and route selection, temperature control, customs. Quote within 2 business hours.',
    summary: 'Delivery from 23 countries and within Russia: route, transport, temperature and lead time control.',
    intro:
      'We deliver pharmaceutical cargo, reference standards and laboratory materials from 23 countries and within Russia. We choose transport for the cargo and route, control temperature and lead times, and handle customs.',
    includes: [
      'International delivery from the Americas, Europe, Asia and the CIS',
      'Delivery within Russia to your warehouse or laboratory',
      'Transport between warehouses and laboratories',
      'Transport and route selection for the cargo',
      'Consolidation of several shipments into one',
      'Cargo tracking and updates at every stage',
    ],
    steps: [
      { title: 'Request', text: 'Tell us the origin and destination, the cargo, its weight and temperature range.' },
      { title: 'Route and quote', text: 'We select transport and route, calculate lead time and cost, and send an offer.' },
      { title: 'Pick-up', text: 'We collect the cargo from the shipper and check the packaging and documents.' },
      { title: 'Transport and customs', text: 'We transport under controlled conditions and clear the cargo at the border.' },
      { title: 'Delivery', text: 'We hand the cargo to the consignee with documents and, if needed, a temperature report.' },
    ],
    related: [
      { label: 'Cold chain', href: '/services/cold-chain/' },
      { label: 'Customs clearance', href: '/services/customs-clearance/' },
      { label: 'Import and export clearance', href: '/services/import-export/' },
    ],
    form: {
      title: 'Get a delivery quote',
      text: 'Enter the route, cargo and temperature range — we will calculate lead time and cost within 2 business hours.',
    },
    imageAlt: 'Truck for pharmaceutical cargo, top view',
  },
  'cold-chain': {
    name: 'Cold chain',
    h1: 'Cold chain for pharmaceutical cargo',
    title: 'Cold chain and temperature-controlled pharma delivery | OGK-CHEM',
    description:
      'Transport of temperature-sensitive cargo at +15…+25, +2…+8, −20 °C and on dry ice: insulated shippers, coolant packs, temperature loggers. Delivery from 23 countries, customs. Quote within 2 business hours.',
    summary: 'Insulated shippers, coolant packs and dry ice, temperature loggers along the whole route.',
    intro:
      'We transport temperature-sensitive cargo under the required temperature range along the whole route — from the manufacturer’s warehouse to your laboratory. Insulated shippers, coolant packs and dry ice, temperature loggers with a trip report.',
    includes: [
      'Insulated packaging chosen for the temperature range and route duration',
      'Ranges +15…+25 °C, +2…+8 °C, −20 °C and dry ice',
      'Temperature loggers and a compliance report',
      'Dry ice shipped as dangerous goods with the required paperwork',
      'Customs documents prepared in advance so the cargo is not delayed',
      'Delivery from 23 countries to your warehouse or laboratory',
    ],
    steps: [
      { title: 'Range and route', text: 'We confirm the temperature range from the manufacturer’s documents, the route and lead time.' },
      { title: 'Packaging and quote', text: 'We select an insulated shipper and coolant with a time margin and send a quote.' },
      { title: 'Dispatch with a logger', text: 'We pack the cargo, start the temperature logger and hand it to the carrier.' },
      { title: 'In-transit control', text: 'We track the cargo and timing, and replace the coolant en route if needed.' },
      { title: 'Delivery and report', text: 'We hand over the cargo together with the logger’s in-transit temperature report.' },
    ],
    table: {
      caption: 'Transport temperature ranges',
      head: ['Range', 'What we ship', 'How we keep it'],
      rows: [
        ['+15…+25 °C', 'Reagents, many reference standards and medicines', 'Insulated shipper, conditioned coolant packs'],
        ['+2…+8 °C', 'Temperature-sensitive standards and medicines', 'Insulated shipper with coolant packs, logger'],
        ['−20 °C', 'Standards and reagents that must stay frozen', 'Frozen coolant packs or dry ice'],
        ['Dry ice, about −78 °C', 'Biological materials and deep-frozen samples', 'Dry ice, shipped as dangerous goods'],
      ],
    },
    faq: [
      {
        q: 'How is compliance with the temperature range confirmed?',
        a: 'We put a temperature logger in every shipment. After delivery we provide a temperature report for the whole time in transit.',
      },
      {
        q: 'What if the route is long?',
        a: 'We choose an insulated shipper with a time margin and, if needed, replace the coolant at an intermediate warehouse.',
      },
    ],
    related: [
      { label: 'Pharmaceutical logistics', href: '/services/pharma-logistics/' },
      { label: 'Reference standards', href: '/catalog/reference-standards/' },
      { label: 'Microorganisms and biological standards', href: '/catalog/biological-standards/' },
      { label: 'Customs clearance', href: '/services/customs-clearance/' },
    ],
    form: {
      title: 'Get a cold chain delivery quote',
      text: 'Enter the route, temperature range, weight and date — we will calculate delivery within 2 business hours.',
    },
    imageAlt: 'Truck for temperature-controlled cargo',
  },
  'customs-clearance': {
    name: 'Customs clearance',
    h1: 'Customs clearance of pharmaceutical cargo',
    title: 'Customs clearance of pharmaceuticals | OGK-CHEM',
    description:
      'Customs clearance of pharmaceuticals, reference standards, reagents and laboratory equipment: HS codes, document review, import permits, duty calculation.',
    summary: 'HS codes, document review, duty calculation, declaration and release.',
    intro:
      'We clear imports of pharmaceuticals, reference standards, reagents and laboratory equipment. We determine HS (TN VED) codes, review the document package before the cargo is shipped and support obtaining permits.',
    includes: [
      'Goods classification and HS code selection',
      'Document package review before shipment',
      'Customs duty calculation',
      'Declaration and support until release',
      'Import permits — where required',
      'Advice on import requirements',
    ],
    steps: [
      { title: 'Cargo description', text: 'Send the product description, invoice and manufacturer documents.' },
      { title: 'Classification and review', text: 'We determine HS codes, check the documents and whether permits are needed.' },
      { title: 'Quote', text: 'We calculate duties and clearance time and send an offer.' },
      { title: 'Declaration', text: 'We file the declaration and support the cargo until release.' },
      { title: 'Release', text: 'We hand the cargo to you or deliver it onward within Russia.' },
    ],
    faq: [
      {
        q: 'What documents are needed for customs clearance?',
        a: 'Usually the contract, invoice, packing list, transport documents and manufacturer documents for the goods. Some goods require permits — the list depends on the HS code.',
      },
    ],
    related: [
      { label: 'HS code classification', href: '/services/tn-ved/' },
      { label: 'Import permits', href: '/services/import-permits/' },
      { label: 'Import and export clearance', href: '/services/import-export/' },
    ],
    form: {
      title: 'Request customs clearance',
      text: 'Describe the goods and route — we will assess documents, duties and timing within 2 business hours.',
    },
    imageAlt: 'Customs stamp',
  },
  'import-export': {
    name: 'Import and export clearance',
    h1: 'Import and export clearance',
    title: 'Import and export clearance for laboratory goods and pharmaceuticals | OGK-CHEM',
    description:
      'Support for import and export of pharmaceutical and laboratory goods: foreign trade documents, logistics, customs clearance. Reply within 2 business hours.',
    summary: 'End-to-end foreign trade deals: documents, logistics, customs.',
    intro:
      'We support foreign trade deals with pharmaceutical and laboratory goods: imports for your laboratory and exports abroad. Documents, logistics and customs from one provider.',
    includes: [
      'Turnkey import: purchase, delivery, customs clearance',
      'Export: document preparation and customs clearance',
      'Foreign trade documents: invoice, packing list, specification',
      'Check of the destination country’s requirements for the goods',
      'Temperature-controlled logistics',
    ],
    steps: [
      { title: 'Task', text: 'Tell us what needs to be delivered, from where and to where.' },
      { title: 'Deal structure', text: 'We propose a supply scheme, documents and timing.' },
      { title: 'Documents', text: 'We prepare foreign trade documents and check the requirements.' },
      { title: 'Delivery and customs', text: 'We transport the cargo and clear it at the border.' },
    ],
    related: [
      { label: 'Customs clearance', href: '/services/customs-clearance/' },
      { label: 'Pharmaceutical logistics', href: '/services/pharma-logistics/' },
      { label: 'HS code classification', href: '/services/tn-ved/' },
    ],
    form: {
      title: 'Discuss import or export',
      text: 'Describe the goods and direction — we will propose a scheme and timing within 2 business hours.',
    },
  },
  'import-permits': {
    name: 'Import permits',
    h1: 'Import permits',
    title: 'Ministry of Health and FSTEC import permits | OGK-CHEM',
    description:
      'We help obtain import permits: the Ministry of Health of Russia for medicinal products for research, FSTEC of Russia for dual-use goods. Document preparation and support.',
    summary: 'We determine which document is needed, prepare the package and support you until it is issued.',
    intro:
      'We help obtain permits for import into Russia: a Ministry of Health of Russia permit to import medicinal products for research, and FSTEC of Russia documents for dual-use goods.',
    includes: [
      'Determining which permit a specific product needs',
      'Ministry of Health of Russia permit to import a batch of medicines for research',
      'FSTEC of Russia documents for dual-use goods',
      'Preparing and filing the document package',
      'Support until the permit is issued',
      'Using the permit during customs clearance',
    ],
    steps: [
      { title: 'Product description', text: 'Send the description, composition, intended use and manufacturer documents.' },
      { title: 'Assessment', text: 'We determine whether a permit is needed and which one, and give the timing.' },
      { title: 'Document package', text: 'We prepare the application and documents and agree them with you.' },
      { title: 'Filing and support', text: 'We file the documents and answer the authority’s queries.' },
      { title: 'Permit', text: 'We obtain the permit and use it to clear the cargo.' },
    ],
    faq: [
      {
        q: 'How do I know whether my product needs a permit?',
        a: 'It depends on the product, its HS code and the purpose of import. Send a description and we will tell you whether a document is needed and which one.',
      },
    ],
    related: [
      { label: 'Supply of medicines for research', href: '/services/research-drug-supply/' },
      { label: 'Customs clearance', href: '/services/customs-clearance/' },
      { label: 'HS code classification', href: '/services/tn-ved/' },
    ],
    form: {
      title: 'Obtain an import permit',
      text: 'Describe the product and choose the authority — we will assess whether a document is needed and give the timing.',
    },
  },
  'tn-ved': {
    name: 'HS code classification',
    h1: 'HS (TN VED) code classification',
    title: 'HS (TN VED) code classification for pharmaceutical goods | OGK-CHEM',
    description:
      'We determine the EAEU HS (TN VED) code for substances, reference standards, reagents and laboratory equipment: classification rationale, duty rates, non-tariff measures.',
    summary: 'EAEU HS code with rationale, duty rates and import requirements.',
    intro:
      'We determine the EAEU HS (TN VED) code for pharmaceutical substances, reference standards, reagents and laboratory equipment — with a rationale based on the description, composition and intended use of the goods.',
    includes: [
      'Analysis of the product description, composition and intended use',
      'Code selection under the General Rules of Interpretation',
      'Written classification rationale',
      'Duty and VAT rates, non-tariff measures for the code',
      'List of documents needed for import',
    ],
    steps: [
      { title: 'Description', text: 'Send the product description, composition and manufacturer documents.' },
      { title: 'Analysis', text: 'We study the product and the applicable classification rules.' },
      { title: 'Code and rationale', text: 'We send the HS code with a rationale.' },
      { title: 'Requirements', text: 'We list duty rates and import documents.' },
    ],
    faq: [
      {
        q: 'What happens if the HS code is wrong?',
        a: 'The declaration may be corrected, additional duties charged and the release of the cargo delayed. That is why it is better to determine the code before shipment.',
      },
    ],
    related: [
      { label: 'Customs clearance', href: '/services/customs-clearance/' },
      { label: 'Import permits', href: '/services/import-permits/' },
    ],
    form: {
      title: 'Find an HS code',
      text: 'Describe the product: what it is, what it consists of and what it is used for. We reply within 2 business hours.',
    },
  },
};

/** Услуги на английском: поля формы, картинки и даты — из русской версии */
export const servicesEn: ServiceContent[] = services.map((ru) => {
  const t = en[ru.slug];
  if (!t) return ru;
  const { imageAlt, form, ...text } = t;
  return {
    ...ru,
    ...text,
    countries: ru.countries ? COUNTRIES_EN : undefined,
    form: { ...ru.form, ...form },
    image: ru.image ? { ...ru.image, alt: imageAlt ?? ru.image.alt } : undefined,
    hasEn: true,
  };
});
