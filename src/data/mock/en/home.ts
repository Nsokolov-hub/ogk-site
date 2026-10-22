import type { HomeContent } from '@/types/content';
import { homeBrands } from '../brands';

/** Контент главной на английском (EN-04). Структура — как у homeContentRu */
export const homeContentEn: HomeContent = {
  hero: {
    slides: [
      {
        id: 'main',
        title: 'Materials, reagents and equipment for pharmaceutical laboratories',
        subtitle: 'End-to-end supply for pharmaceutical companies',
        ctas: [
          { label: 'Place an order', href: '#request', variant: 'primary', icon: 'plus' },
          { label: 'Contact us', href: '/contacts/', variant: 'secondary', icon: 'dot' },
        ],
        imageMode: 'cover',
        image: { src: '/images/home/hero-1.jpg', alt: 'Reference standard vial with a green cap', width: 2880, height: 1728 },
      },
      {
        id: 'standards',
        title: 'Reference standards from leading manufacturers',
        subtitle: 'EDQM, USP, LGC, Merck and other brands — supplied to order from manufacturer catalogues, with documents and controlled storage conditions',
        ctas: [{ label: 'Browse the catalogue', href: '/catalog/reference-standards/', variant: 'primary', icon: 'arrow' }],
        imageMode: 'object',
        image: { src: '/images/home/hero-2.png', alt: 'Merck reagent bottle', width: 824, height: 1478 },
      },
      {
        id: 'logistics',
        title: 'Cold chain logistics from 23 countries',
        subtitle: 'Insulated shippers, coolant packs and temperature loggers, customs clearance and import permits',
        ctas: [
          { label: 'Get a delivery quote', href: '/services/cold-chain/', variant: 'primary', icon: 'arrow' },
          { label: 'All services', href: '/services/', variant: 'secondary', icon: 'dot' },
        ],
        imageMode: 'object',
        image: { src: '/images/home/hero-3.png', alt: 'Truck for pharmaceutical cargo', width: 2082, height: 824 },
      },
    ],
    search: {
      title: 'Find an item by name, catalogue number or CAS',
      examples: ['Paracetamol', '58-08-2', 'PHR6721', 'XBridge C18'],
    },
    facts: [
      { value: '60+', label: 'global manufacturers' },
      { value: '23', label: 'supply countries' },
      { value: '2 hours', label: 'to reply to a request' },
    ],
  },

  products: {
    title: 'Product',
    accent: 'catalogue',
    subtitle: 'Reference standards, reagents, chromatography supplies and equipment from leading manufacturers',
  },

  brands: {
    title: 'Wide',
    accent: 'range',
    subtitle: 'For every production task',
    items: homeBrands,
  },

  promo: {
    title: 'Looking for a specific product?',
    text: 'A large selection of products in the catalogue',
    cta: { label: 'Browse the catalogue', href: '/catalog/', variant: 'primary', icon: 'arrow' },
    image: { src: '/images/home/promo-vials.png', alt: 'EDQM and USP reference standard vials', width: 1426, height: 972 },
  },

  quality: {
    title: 'Best',
    accent: 'quality',
    subtitle: 'We offer our clients only verified products',
    items: [
      { id: 'purchase', title: 'Sourcing', icon: 'globe', text: 'From the USA, Europe, Asia, Latin America and other countries. We handle customs procedures and logistics' },
      { id: 'documents', title: 'Documents', icon: 'file', text: 'We provide all the documentation you need. Certification and control at every stage in line with the rules' },
      { id: 'delivery', title: 'Delivery', icon: 'map', text: 'To any region of Russia through established logistics. We keep the temperature range, lead times and storage conditions' },
    ],
  },

  services: {
    title: 'Turnkey',
    accent: 'service',
    subtitle: 'A full range of services for pharmaceutical companies',
    items: [
      {
        id: 'supply',
        title: 'Supply of medicinal products for research',
        href: '/services/research-drug-supply/',
        text: 'We supply medicinal products to Russia for research purposes, as well as reference standards, reagents, chromatography consumables (columns, filters, guard columns, fittings), reference medicinal products for laboratory testing, laboratory containers and auxiliary equipment. Products of leading global brands meet strict international standards, and local manufacturers help cover laboratory needs without compromising quality.',
        captionLabel: 'We supply:',
        chips: [
          'EDQM', 'USP', 'Merck', 'LGC', 'BioOrganics', 'SynZeal', 'SCIEX', 'Waters', 'Macklin',
          'Clearsynth', 'Aozeal', 'Agilent', 'Welch', 'Dayang Chem', 'ATCC', 'British Pharmacopoeia',
          'Shimadzu', 'TRC',
        ].map((label) => ({ label })),
        image: { src: '/images/home/service-supply.png', alt: 'Reagent bottle', width: 824, height: 1478 },
      },
      {
        id: 'logistics',
        title: 'Logistics and cold chain',
        href: '/services/cold-chain/',
        text: 'Pharmaceutical delivery with full temperature control. We maintain the cold chain with insulated shippers and coolant packs and monitor temperature with data loggers. We work with partners in the Americas, Europe, Asia and the CIS, choose transport for the cargo and route, and adapt solutions to different shipment types and customer requirements.',
        captionLabel: 'We deliver from:',
        chips: [
          'USA', 'Canada', 'United Kingdom', 'France', 'Sweden', 'Germany', 'Norway', 'China',
          'Armenia', 'Georgia', 'Netherlands', 'Switzerland', 'Russia', 'Kazakhstan', 'Uzbekistan',
          'Azerbaijan', 'Austria', 'Belgium', 'Australia', 'Japan', 'South Korea', 'Italy', 'Spain',
        ].map((label) => ({ label })),
        image: { src: '/images/home/service-logistics.png', alt: 'Truck, top view', width: 824, height: 2082 },
      },
      {
        id: 'customs',
        title: 'Customs',
        href: '/services/customs-clearance/',
        text: 'We clear pharmaceuticals and related goods through customs. We determine HS (TN VED) codes, check the document package and support obtaining permits for import into the Russian Federation. We minimise the risk of delays, ensure regulatory compliance and control the process at every stage.',
        captionLabel: 'We can:',
        chips: [
          { label: 'Import clearance', href: '/services/import-export/' },
          { label: 'Export clearance', href: '/services/import-export/' },
          { label: 'Import permit — Ministry of Health', href: '/services/import-permits/' },
          { label: 'Import permit — FSTEC', href: '/services/import-permits/' },
          { label: 'HS code classification', href: '/services/tn-ved/' },
          { label: 'Document package review' },
          { label: 'Consulting' },
        ],
        image: { src: '/images/home/service-customs.png', alt: 'Stamp', width: 824, height: 966 },
      },
    ],
  },

  whyUs: {
    title: 'Why',
    accent: 'choose us',
    textAccent: 'OGK-CHEM',
    text: 'is a specialised company that provides pharmaceutical manufacturers with everything they need for accurate laboratory research and development. We help clients optimise procurement while guaranteeing the quality of supplied products. Our work is built on a customer-first approach and continuous improvement of our service.',
    items: [
      { id: 'expertise', title: 'Expertise', icon: 'users', text: 'Our team has many years of experience in the pharmaceutical industry and will help you find the right solutions for your laboratory tasks' },
      { id: 'quality', title: 'Quality assurance', icon: 'check', text: 'We work only with verified manufacturers and supply quality products' },
      { id: 'speed', title: 'Speed', icon: 'zap', text: 'Our logistics network delivers materials quickly to any part of Russia under the right transport conditions' },
      { id: 'individual', title: 'Tailored approach', icon: 'loader', text: 'We design solutions around each client and the specifics of their work' },
    ],
  },

  capabilities: {
    title: 'With us you can',
    items: [
      { id: 'c1', prefix: 'Order', accent: 'reference standards', suffix: 'for your laboratory', href: '/catalog/reference-standards/' },
      { id: 'c2', prefix: 'Order', accent: 'reagents', suffix: 'for your laboratory', href: '/catalog/reagents/' },
      { id: 'c3', prefix: 'Order', accent: 'consumables', suffix: 'for chromatography', href: '/catalog/chromatography/' },
      { id: 'c4', prefix: 'Order', accent: 'reference medicinal products', suffix: 'for laboratory studies', href: '/catalog/reference-drugs/' },
      { id: 'c5', prefix: 'Order', accent: 'microorganisms and biological standards', suffix: 'for laboratory studies', href: '/catalog/biological-standards/' },
      { id: 'c6', prefix: 'Order', accent: 'laboratory equipment', suffix: 'for your laboratory', href: '/catalog/laboratory-equipment/' },
      { id: 'c7', prefix: 'Buy an annual', accent: 'online pharmacopoeia subscription', suffix: 'and reference books', href: '/catalog/pharmacopeias/' },
      { id: 'c8', prefix: 'Order', accent: 'delivery', suffix: 'of your cargo to your warehouse', href: '/services/pharma-logistics/' },
      { id: 'c9', prefix: 'Order', accent: 'transport', suffix: 'between warehouses or laboratories', href: '/services/pharma-logistics/' },
      { id: 'c10', prefix: 'Order', accent: 'insulated boxes and coolant packs', suffix: 'for your cargo', href: '/services/cold-chain/' },
      { id: 'c11', prefix: 'Order', accent: 'customs clearance', suffix: 'for your cargo', href: '/services/customs-clearance/' },
      { id: 'c12', prefix: 'Obtain', accent: 'import permits', suffix: 'for your cargo', href: '/services/import-permits/' },
    ],
  },

  request: {
    title: 'Send your',
    accent: 'request',
    promises: [
      { id: 'fast', icon: 'zap', title: 'Fast processing', text: 'Standard response time is up to 2 business hours' },
      { id: 'call', icon: 'phone', title: 'We will contact you', text: 'To clarify the details of your request' },
      { id: 'manager', icon: 'user', title: 'A dedicated manager', text: 'To handle your request' },
      { id: 'offer', icon: 'mail', title: 'A commercial quotation', text: 'Based on your request' },
    ],
  },

  subscribe: {
    title: 'Subscribe to our',
    accent: 'newsletter',
    text: 'New catalogue items, reviews of standards and pharma logistics news',
  },
};
