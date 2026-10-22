import type { BrandContent } from '@/types/content';
import { brandContent } from '../brand-content';

/**
 * Страницы брендов на английском (EN-04). Логотип, волна, «фасовка под запрос» и даты — из русской версии.
 * Статус официального партнёрства не указываем, как и в русской версии (NFR-09).
 */

const RS = '/catalog/reference-standards';
const CH = '/catalog/chromatography';

type Text = Pick<BrandContent, 'h1' | 'title' | 'description' | 'summary' | 'intro' | 'text' | 'groups' | 'faq' | 'country'>;

const en: Record<string, Text> = {
  edqm: {
    country: 'France, Strasbourg',
    h1: 'EDQM products: reference standards and pharmacopoeia',
    title: 'EDQM — European Pharmacopoeia reference standards | OGK-CHEM',
    description: 'EDQM reference standards (CRS) and the European Pharmacopoeia: supplied to order to Russia with documents and cold chain. Request a quotation — reply within 2 business hours.',
    summary: 'European Pharmacopoeia reference standards (CRS) and Ph. Eur.',
    intro: 'The European Directorate for the Quality of Medicines & HealthCare (EDQM) publishes the European Pharmacopoeia and establishes reference standards for tests according to its monographs. We supply CRS to order under the required storage conditions.',
    text: [
      'EDQM is part of the Council of Europe. It publishes the European Pharmacopoeia (Ph. Eur.) and establishes chemical reference substances (CRS), biological reference preparations (BRP) and standards for chromatographic system suitability. They are used in tests where the Ph. Eur. monographs specify them.',
      'EDQM standards come in a fixed pack size. Batch suitability is confirmed by the current EDQM catalogue rather than an expiry date on the label — we check the batch status before shipment and state it in the quotation.',
      'Many CRS must be stored at +2…+8 °C or −20 °C. We ship them in insulated boxes with coolant packs and temperature loggers and handle customs clearance.',
    ],
    groups: [
      { label: 'EDQM reference standards', href: `${RS}/edqm/` },
      { label: 'Impurity standards', href: `${RS}/impurity-standards/` },
      { label: 'European Pharmacopoeia', href: '/catalog/pharmacopeias/' },
    ],
    faq: [
      { q: 'How do I know that a CRS batch is current?', a: 'EDQM publishes the batch status in its catalogue. We check it before shipment and state it in the quotation.' },
      { q: 'Can I order an EDQM standard in a different pack size?', a: 'No, EDQM issues standards in one fixed pack size. If you need more substance, order several vials.' },
    ],
  },
  usp: {
    country: 'USA, Rockville',
    h1: 'USP products: reference standards and USP–NF',
    title: 'USP — United States Pharmacopeia reference standards | OGK-CHEM',
    description: 'USP Reference Standards and USP–NF: supplied to order to Russia with documents and controlled storage conditions. Request a quotation — reply within 2 business hours.',
    summary: 'United States Pharmacopeia reference standards and USP–NF',
    intro: 'The United States Pharmacopeial Convention (USP) publishes USP–NF and issues reference standards for tests according to its monographs. We supply USP Reference Standards to order.',
    text: [
      'USP is a non-profit scientific organisation that develops quality standards for medicines and publishes USP–NF. USP reference standards are used in the tests specified in USP–NF monographs and general chapters.',
      'USP standards come in a fixed pack size. USP confirms lot suitability through its catalogue — we check the lot status before shipment.',
      'If your method follows the European Pharmacopoeia, you need an EDQM standard instead.',
    ],
    groups: [
      { label: 'USP reference standards', href: `${RS}/usp/` },
      { label: 'Pharmacopoeias and reference books', href: '/catalog/pharmacopeias/' },
    ],
  },
  'british-pharmacopoeia': {
    country: 'United Kingdom, London',
    h1: 'British Pharmacopoeia products',
    title: 'British Pharmacopoeia — BPCRS reference standards and pharmacopoeia | OGK-CHEM',
    description: 'British Pharmacopoeia chemical reference substances (BPCRS) and BP editions: supplied to order with documents. Request a quotation.',
    summary: 'BPCRS reference standards and British Pharmacopoeia editions',
    intro: 'The British Pharmacopoeia (BP) issues BPCRS chemical reference substances for tests according to its monographs. We supply BP standards and editions to order.',
    text: [
      'The British Pharmacopoeia is the national pharmacopoeia of the United Kingdom, published by the country’s medicines regulator. BPCRS chemical reference substances are used in tests where BP monographs specify them.',
      'In addition to standards, we supply print and online editions of the British Pharmacopoeia with an annual subscription.',
    ],
    groups: [
      { label: 'British Pharmacopoeia reference standards', href: `${RS}/british-pharmacopoeia/` },
      { label: 'Pharmacopoeias and reference books', href: '/catalog/pharmacopeias/' },
    ],
  },
  lgc: {
    country: 'United Kingdom',
    h1: 'LGC products for laboratories',
    title: 'LGC — reference standards and impurity standards | OGK-CHEM',
    description: 'LGC Standards reference materials: API and impurity standards in several pack sizes. Supplied to order with documents, request a quotation.',
    summary: 'API and impurity standards in several pack sizes',
    intro: 'LGC Standards produces reference standards for pharmaceutical analysis, including pharmacopoeial impurity standards. We supply them to order in the manufacturer’s pack sizes.',
    text: [
      'The LGC catalogue includes API, impurity and metabolite standards with the manufacturer’s certificate of analysis. Unlike pharmacopoeial standards, many LGC items are available in several pack sizes: 10, 25, 50 or 100 mg.',
      'LGC standards are often used to identify impurity peaks and validate HPLC methods. We will select standards for a pharmacopoeial monograph or your in-house method.',
    ],
    groups: [
      { label: 'LGC reference standards', href: `${RS}/lgc/` },
      { label: 'Impurity standards', href: `${RS}/impurity-standards/` },
    ],
  },
  merck: {
    country: 'Germany, Darmstadt',
    h1: 'Merck products for laboratories',
    title: 'Merck — secondary standards, solvents and reagents | OGK-CHEM',
    description: 'Merck pharmaceutical secondary standards, HPLC and LC-MS solvents and reagents: supplied to order with documents, request a quotation.',
    summary: 'Secondary standards, HPLC solvents and reagents',
    intro: 'Merck is a German science and technology company. For pharmaceutical laboratories we supply its secondary standards, chromatography solvents and analytical reagents.',
    text: [
      'Merck Pharmaceutical Secondary Standards (Certified Reference Materials) are traceable to primary pharmacopoeial standards and convenient for routine quality control: they cost less than primary standards and come with a certificate of analysis.',
      'Gradient-grade HPLC and LC-MS solvents, acids and salts for mobile phases are supplied in the manufacturer’s pack sizes — from 100 mL to 2.5 L.',
    ],
    groups: [
      { label: 'Merck secondary standards', href: `${RS}/merck/` },
      { label: 'Reagents', href: '/catalog/reagents/' },
    ],
  },
  waters: {
    country: 'USA, Milford',
    h1: 'Waters products for laboratories',
    title: 'Waters — HPLC columns and consumables | OGK-CHEM',
    description: 'XBridge, SunFire, Symmetry and ACQUITY UPLC columns, guard columns, vials and Waters HPLC equipment. Selection for your method, supplied to order, request a quotation.',
    summary: 'HPLC and UHPLC columns and guard columns, vials, systems',
    intro: 'Waters is a US manufacturer of liquid chromatography and mass spectrometry instruments and consumables. We supply Waters columns, guard columns and consumables to order.',
    text: [
      'The Waters range includes XBridge and ACQUITY UPLC BEH hybrid-particle columns with a wide pH range, SunFire and Symmetry silica columns, VanGuard and Sentry guard columns, and certified LC-MS vials.',
      'We will select a column for your method: send the phase, dimensions, particle size and separation conditions, and we will offer a Waters column or an equivalent with the same USP classification.',
    ],
    groups: [
      { label: 'HPLC columns', href: `${CH}/hplc-columns/` },
      { label: 'Guard columns', href: `${CH}/precolumns/` },
      { label: 'Laboratory glassware and containers', href: '/catalog/laboratory-glassware/' },
      { label: 'Laboratory equipment', href: '/catalog/laboratory-equipment/' },
    ],
  },
  agilent: {
    country: 'USA, Santa Clara',
    h1: 'Agilent products for laboratories',
    title: 'Agilent — ZORBAX and Poroshell columns, HPLC consumables | OGK-CHEM',
    description: 'ZORBAX and InfinityLab Poroshell columns, guard columns, filters, vials and Agilent HPLC modules. Selection for your method, supplied to order, request a quotation.',
    summary: 'ZORBAX and Poroshell columns, filters, vials, HPLC modules',
    intro: 'Agilent Technologies is a US manufacturer of analytical instruments and consumables. We supply Agilent columns, guard columns, filters, vials and HPLC modules.',
    text: [
      'ZORBAX Eclipse Plus and ZORBAX SB columns are classic reversed-phase columns on high-purity silica; InfinityLab Poroshell 120 superficially porous columns give near-UHPLC efficiency at moderate pressure.',
      'Besides columns, we supply syringe filters, vials with caps, fittings and 1260 Infinity II system modules.',
    ],
    groups: [
      { label: 'HPLC columns', href: `${CH}/hplc-columns/` },
      { label: 'Filters', href: `${CH}/filters/` },
      { label: 'Fittings', href: `${CH}/fittings/` },
      { label: 'Laboratory equipment', href: '/catalog/laboratory-equipment/' },
    ],
  },
  shimadzu: {
    country: 'Japan, Kyoto',
    h1: 'Shimadzu products for laboratories',
    title: 'Shimadzu — Shim-pack columns and HPLC equipment | OGK-CHEM',
    description: 'Shim-pack GIST columns, HPLC systems and Shimadzu spectrophotometers: supplied to order, selection for your task, request a quotation.',
    summary: 'Shim-pack columns, HPLC systems, spectrophotometers',
    intro: 'Shimadzu is a Japanese manufacturer of analytical instruments. We supply Shim-pack columns, HPLC systems and Shimadzu spectrophotometers to order.',
    text: [
      'Shim-pack GIST columns are available with C18, Phenyl and other phases and suit routine pharmacopoeial methods. For quality control laboratories we also supply integrated HPLC systems and UV spectrophotometers.',
      'We agree equipment supply together with installation and accompanying documents — the terms are stated in the quotation.',
    ],
    groups: [
      { label: 'HPLC columns', href: `${CH}/hplc-columns/` },
      { label: 'Laboratory equipment', href: '/catalog/laboratory-equipment/' },
    ],
  },
  sciex: {
    country: 'USA',
    h1: 'SCIEX products for laboratories',
    title: 'SCIEX — mass spectrometry and consumables | OGK-CHEM',
    description: 'SCIEX LC-MS/MS consumables and equipment: supplied to order by the manufacturer’s catalogue numbers. Request a quotation.',
    summary: 'LC-MS/MS equipment and consumables',
    intro: 'SCIEX produces mass spectrometers and capillary electrophoresis systems for pharmaceutical analysis. We supply SCIEX consumables and equipment to order.',
    text: ['We supply SCIEX items by the manufacturer’s catalogue numbers: send a list and we will check availability and send one quotation for everything.'],
    groups: [{ label: 'Laboratory equipment', href: '/catalog/laboratory-equipment/' }],
  },
  atcc: {
    country: 'USA, Manassas',
    h1: 'ATCC microorganisms and biological standards',
    title: 'ATCC — reference microbial strains | OGK-CHEM',
    description: 'ATCC reference strains for culture media control and microbiological testing: supplied to order with customs clearance and import permits. Request a quotation.',
    summary: 'Reference strains for microbiological control',
    intro: 'The American Type Culture Collection (ATCC) is a non-profit biological resource centre. We supply ATCC reference strains to microbiological laboratories.',
    text: [
      'ATCC reference strains — for example, Escherichia coli ATCC 25922 or Staphylococcus aureus ATCC 6538 — are used for culture media quality control, microbial limit tests and antimicrobial susceptibility testing.',
      'Importing microorganisms requires documents. We handle customs clearance and, where needed, import permits.',
    ],
    groups: [
      { label: 'Microorganisms and biological standards', href: '/catalog/biological-standards/' },
      { label: 'Import permits', href: '/services/import-permits/' },
    ],
  },
  welch: {
    country: 'China',
    h1: 'Welch columns and consumables',
    title: 'Welch — Ultimate HPLC columns | OGK-CHEM',
    description: 'Welch Ultimate XB-C18, AQ-C18, HILIC columns and guard columns for HPLC: supplied to order, equivalent selection, request a quotation.',
    summary: 'Ultimate HPLC columns and guard columns',
    intro: 'Welch Materials produces HPLC columns and sample preparation materials. Welch columns are often chosen as equivalents to other manufacturers’ columns with the same USP classification.',
    text: [
      'The Ultimate range includes XB-C18 columns for a wide range of tasks, AQ-C18 for highly aqueous mobile phases and HILIC Amide for polar compounds. Guard columns with the same phase are available.',
      'Send us your method and we will offer a Welch column as an equivalent and explain the differences in characteristics.',
    ],
    groups: [
      { label: 'HPLC columns', href: `${CH}/hplc-columns/` },
      { label: 'Guard columns', href: `${CH}/precolumns/` },
      { label: 'Filters', href: `${CH}/filters/` },
    ],
  },
  synzeal: {
    country: 'India',
    h1: 'SynZeal impurity standards',
    title: 'SynZeal — pharmaceutical impurity standards | OGK-CHEM',
    description: 'SynZeal pharmacopoeial impurity, metabolite and labelled compound standards in any pack size on request. Supplied to order, request a quotation.',
    summary: 'Impurity and metabolite standards, any pack size on request',
    intro: 'SynZeal synthesises pharmaceutical impurity, metabolite and labelled compound standards. Any pack size on request.',
    text: [
      'The manufacturer produces the standard in the quantity you need: in addition to standard 10 and 25 mg packs you can order your own — enter the quantity in the cart. We state the production time and accompanying data in the quotation.',
    ],
    groups: [{ label: 'Impurity standards', href: `${RS}/impurity-standards/` }],
  },
  clearsynth: {
    country: 'India',
    h1: 'Clearsynth impurity standards',
    title: 'Clearsynth — impurity standards and labelled compounds | OGK-CHEM',
    description: 'Clearsynth impurity, metabolite and stable isotope-labelled compound standards in any pack size on request. Request a quotation.',
    summary: 'Impurities, metabolites and labelled compounds on request',
    intro: 'Clearsynth synthesises pharmaceutical impurity, metabolite and labelled compound standards. Any pack size on request.',
    text: ['Enter the quantity you need when ordering and the manufacturer will produce the standard to your request. We state the lead time and documents in the quotation.'],
    groups: [{ label: 'Impurity standards', href: `${RS}/impurity-standards/` }],
  },
  trc: {
    country: 'Canada, Toronto',
    h1: 'TRC standards and labelled compounds',
    title: 'TRC (Toronto Research Chemicals) — impurities and labelled compounds | OGK-CHEM',
    description: 'Toronto Research Chemicals impurity, metabolite and labelled compound standards: supplied to order, any pack size on request. Request a quotation.',
    summary: 'Metabolites and labelled compounds',
    intro: 'Toronto Research Chemicals (TRC) produces organic compounds for research: metabolites, impurities and labelled compounds. We supply them to order.',
    text: ['TRC labelled compounds — for example, deuterated analogues of APIs — are used as internal standards in LC-MS/MS. Enter the quantity you need when ordering.'],
    groups: [{ label: 'Impurity standards', href: `${RS}/impurity-standards/` }],
  },
  aozeal: {
    h1: 'Aozeal impurity standards',
    title: 'Aozeal — pharmaceutical impurity standards | OGK-CHEM',
    description: 'Aozeal pharmaceutical impurity standards in any pack size on request: supplied to order with documents, request a quotation.',
    summary: 'Impurity standards, any pack size on request',
    intro: 'Aozeal produces pharmaceutical impurity standards. Any pack size on request.',
    text: ['Send the impurity name, CAS or a reference to the pharmacopoeial monograph and we will check availability and synthesis time.'],
    groups: [{ label: 'Impurity standards', href: `${RS}/impurity-standards/` }],
  },
  bioorganics: {
    h1: 'BioOrganics standards',
    title: 'BioOrganics — impurity standards and labelled compounds | OGK-CHEM',
    description: 'BioOrganics impurity and labelled compound standards in any pack size on request: supplied to order, request a quotation.',
    summary: 'Impurities and labelled compounds on request',
    intro: 'BioOrganics produces impurity standards and labelled compounds for pharmaceutical analysis. Any pack size on request.',
    text: ['Enter the quantity you need when ordering and the pack will be prepared to your request.'],
    groups: [{ label: 'Impurity standards', href: `${RS}/impurity-standards/` }],
  },
  macklin: {
    country: 'China, Shanghai',
    h1: 'Macklin reagents',
    title: 'Macklin — laboratory reagents | OGK-CHEM',
    description: 'Macklin laboratory reagents: solvents, salts, acids and indicators for pharmaceutical laboratories. Supplied to order, request a quotation.',
    summary: 'Laboratory reagents and indicators',
    intro: 'Macklin is a Chinese manufacturer of laboratory reagents. We supply Macklin solvents, salts, acids and indicators to order.',
    text: ['Macklin reagents are often chosen as an economical option for routine laboratory tasks. The reagent grade (ACS, AR, HPLC) is stated in the item name.'],
    groups: [{ label: 'Reagents', href: '/catalog/reagents/' }],
  },
  dwk: {
    country: 'Germany',
    h1: 'DWK Life Sciences laboratory glassware',
    title: 'DWK Life Sciences — DURAN laboratory glassware | OGK-CHEM',
    description: 'DURAN volumetric flasks, beakers and laboratory bottles from DWK Life Sciences: supplied to order, request a quotation.',
    summary: 'DURAN laboratory glassware',
    intro: 'DWK Life Sciences produces borosilicate laboratory glassware under the DURAN, WHEATON and KIMBLE brands. We supply glassware to order.',
    text: ['Class A volumetric flasks, beakers and DURAN laboratory bottles are supplied individually and in packs.'],
    groups: [{ label: 'Laboratory glassware and containers', href: '/catalog/laboratory-glassware/' }],
  },
};

/** Бренды на английском: если перевода нет, остаётся русский текст и hasEn = false */
export const brandContentEn: BrandContent[] = brandContent.map((ru) => {
  const t = en[ru.slug];
  return t ? { ...ru, ...t, hasEn: true } : ru;
});

export const brandsWithEn = new Set(Object.keys(en));
