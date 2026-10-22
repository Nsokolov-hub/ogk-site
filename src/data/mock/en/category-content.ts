import type { CategoryContent, SeoLanding } from '@/types/content';
import { categoryContent } from '../category-content';

/**
 * Разделы каталога и SEO-посадочные на английском (EN-04). Набор фильтров берётся из русской версии —
 * он общий для обоих языков. Переведённый раздел получает hreflang и попадает в Sitemap /en/.
 */

const DELIVERY_STANDARDS = [
  'Supplied to order from manufacturer catalogues — lead time is stated in the quotation',
  'Storage conditions are kept in transit: +2…+8 °C, −20 °C, dry ice',
  'Accompanying documents: batch certificate of analysis (CoA), safety data sheet (SDS)',
  'Delivery to any region of Russia; documents for public procurement under 44-FZ and 223-FZ',
];

const DELIVERY_GENERAL = [
  'Supplied to order from manufacturer catalogues — lead time is stated in the quotation',
  'Delivery to any region of Russia',
  'Documents for public procurement under 44-FZ and 223-FZ',
];

const FAQ_COMMON = [
  {
    q: 'Why are there no prices on the website?',
    a: 'The price depends on pack size, quantity, delivery terms and exchange rates. Add items to the quote cart and a manager will calculate the supply and send a quotation within 2 business hours.',
  },
  {
    q: 'Can I order an item that is not on the website?',
    a: 'Yes. Send a request with the catalogue number or CAS and we will supply it to order from the manufacturer’s catalogue.',
  },
  {
    q: 'Can I get a certificate of analysis for a specific batch?',
    a: 'Yes, we provide the batch CoA on request — mention it in the comment to your request.',
  },
];

const DOCS = [
  { title: 'Company details (in Russian)', href: '/files/kartochka.pdf' },
  { title: 'Privacy policy (in Russian)', href: '/files/politika.pdf' },
];

const RELATED_SERVICES = [
  { label: 'Cold chain', href: '/services/cold-chain/' },
  { label: 'Customs clearance', href: '/services/customs-clearance/' },
  { label: 'Import permits', href: '/services/import-permits/' },
];

type En = Omit<CategoryContent, 'facets'>;

const en: Record<string, En> = {
  '': {
    h1: 'Catalogue',
    title: 'Catalogue: reference standards, reagents and laboratory equipment | OGK-CHEM',
    description:
      'Reference standards, reagents, chromatography consumables, equipment and pharmacopoeias for pharmaceutical laboratories. Search by catalogue number and CAS, request a quotation.',
    intro: 'Reference standards, reagents, chromatography supplies and equipment from leading manufacturers. Search by catalogue number or CAS — or add items to the quote cart.',
    delivery: DELIVERY_GENERAL,
    faq: FAQ_COMMON,
    documents: DOCS,
    related: [
      { label: 'EDQM reference standards', href: '/catalog/reference-standards/edqm/' },
      { label: 'HPLC columns', href: '/catalog/chromatography/hplc-columns/' },
      ...RELATED_SERVICES,
    ],
  },
  'reference-standards': {
    h1: 'Reference standards for laboratories',
    title: 'Reference standards for laboratories — supply to Russia | OGK-CHEM',
    description:
      'Pharmacopoeial and secondary reference standards from EDQM, USP, BP, LGC, Merck and impurity standards. Supplied to order with documents and controlled storage conditions.',
    intro: 'Pharmacopoeial reference standards from EDQM, USP and British Pharmacopoeia, secondary standards and impurity standards. Supplied to order with controlled storage conditions.',
    seoText: [
      'Reference standards are needed for identification, assay and impurity control of medicinal products. EDQM, USP and British Pharmacopoeia standards are used in tests according to the corresponding pharmacopoeial monographs.',
      'Secondary standards (for example, Pharmaceutical Secondary Standards) are traceable to primary pharmacopoeial standards and suit routine control. Custom synthesis manufacturers supply impurity standards and labelled compounds in any pack size on request.',
    ],
    delivery: DELIVERY_STANDARDS,
    faq: [
      ...FAQ_COMMON,
      {
        q: 'How do EDQM standards differ from USP?',
        a: 'EDQM issues European Pharmacopoeia reference standards and USP issues United States Pharmacopeia standards. The choice depends on the monograph you are testing against.',
      },
    ],
    documents: DOCS,
    related: [
      { label: 'Impurity standards', href: '/catalog/reference-standards/impurity-standards/' },
      { label: 'HPLC columns', href: '/catalog/chromatography/hplc-columns/' },
      { label: 'Reagents', href: '/catalog/reagents/' },
      ...RELATED_SERVICES,
    ],
  },
  'reference-standards/edqm': {
    h1: 'EDQM reference standards',
    title: 'EDQM reference standards — supply to Russia | OGK-CHEM',
    description: 'European Pharmacopoeia reference standards (EDQM CRS): supplied to order to Russia with documents and controlled storage conditions. Request a quotation.',
    intro: 'European Pharmacopoeia chemical reference substances (CRS), supplied in the manufacturer’s fixed pack size.',
    delivery: DELIVERY_STANDARDS,
    faq: FAQ_COMMON,
    documents: DOCS,
    related: [
      { label: 'USP reference standards', href: '/catalog/reference-standards/usp/' },
      { label: 'Impurity standards', href: '/catalog/reference-standards/impurity-standards/' },
      ...RELATED_SERVICES,
    ],
  },
  'reference-standards/usp': {
    h1: 'USP reference standards',
    title: 'USP reference standards — supply for laboratories | OGK-CHEM',
    description: 'United States Pharmacopeia reference standards (USP RS): supplied to order with documents and controlled storage conditions. Request a quotation.',
    intro: 'United States Pharmacopeia Reference Standards in the manufacturer’s fixed pack size.',
    delivery: DELIVERY_STANDARDS,
    faq: FAQ_COMMON,
    documents: DOCS,
    related: [
      { label: 'EDQM reference standards', href: '/catalog/reference-standards/edqm/' },
      { label: 'Impurity standards', href: '/catalog/reference-standards/impurity-standards/' },
      ...RELATED_SERVICES,
    ],
  },
  'reference-standards/british-pharmacopoeia': {
    h1: 'British Pharmacopoeia reference standards',
    title: 'British Pharmacopoeia reference standards — OGK-CHEM',
    description: 'British Pharmacopoeia chemical reference substances (BPCRS): supplied to order with documents. Request a quotation.',
    intro: 'British Pharmacopoeia chemical reference substances (BPCRS).',
    delivery: DELIVERY_STANDARDS,
    faq: FAQ_COMMON,
    documents: DOCS,
    related: [{ label: 'Pharmacopoeias and reference books', href: '/catalog/pharmacopeias/' }, ...RELATED_SERVICES],
  },
  'reference-standards/lgc': {
    h1: 'LGC reference standards',
    title: 'LGC reference standards — supply | OGK-CHEM',
    description: 'LGC reference standards: supplied to order in several pack sizes, with documents. Request a quotation.',
    intro: 'LGC reference standards in a choice of pack sizes.',
    delivery: DELIVERY_STANDARDS,
    faq: FAQ_COMMON,
    documents: DOCS,
    related: RELATED_SERVICES,
  },
  'reference-standards/merck': {
    h1: 'Merck reference standards',
    title: 'Merck secondary reference standards — supply | OGK-CHEM',
    description: 'Merck Pharmaceutical Secondary Standards: supplied to order with documents. Request a quotation.',
    intro: 'Pharmaceutical Secondary Standards; Certified Reference Materials.',
    delivery: DELIVERY_STANDARDS,
    faq: FAQ_COMMON,
    documents: DOCS,
    related: [{ label: 'Merck products', href: '/brands/merck/' }, ...RELATED_SERVICES],
  },
  'reference-standards/impurity-standards': {
    h1: 'Impurity standards',
    title: 'Impurity standards from SynZeal, Clearsynth, TRC and others — OGK-CHEM',
    description: 'Pharmacopoeial impurity, metabolite and labelled compound standards. Any pack size on request. Supplied to order, request a quotation.',
    intro: 'Impurities, metabolites and labelled compounds from custom synthesis manufacturers. Any pack size on request — enter the quantity you need in the cart.',
    delivery: DELIVERY_STANDARDS,
    faq: [
      ...FAQ_COMMON,
      {
        q: 'Can I order a non-standard pack size?',
        a: 'Yes. For impurity standards choose “Custom pack size” and enter the quantity in mg, g or mL.',
      },
    ],
    documents: DOCS,
    related: RELATED_SERVICES,
  },
  reagents: {
    h1: 'Reagents for pharmaceutical laboratories',
    title: 'Laboratory reagents for pharmaceutical QC — supply | OGK-CHEM',
    description: 'HPLC and LC-MS solvents, acids, salts and indicators for pharmaceutical laboratories. Supplied to order, request a quotation.',
    intro: 'HPLC and LC-MS solvents, acids, salts, buffer components and indicators.',
    delivery: DELIVERY_GENERAL,
    faq: FAQ_COMMON,
    documents: DOCS,
    related: [{ label: 'HPLC columns', href: '/catalog/chromatography/hplc-columns/' }, ...RELATED_SERVICES],
  },
  chromatography: {
    h1: 'Chromatography consumables',
    title: 'Chromatography consumables — OGK-CHEM',
    description: 'HPLC columns and guard columns, filters and fittings from Waters, Agilent, Shimadzu and Welch. Selection for your method, request a quotation.',
    intro: 'HPLC and UHPLC columns and guard columns, syringe filters and fittings. We will help you choose a column for your method.',
    delivery: DELIVERY_GENERAL,
    faq: FAQ_COMMON,
    documents: DOCS,
    related: [{ label: 'HPLC solvents', href: '/catalog/reagents/' }, ...RELATED_SERVICES],
  },
  'chromatography/hplc-columns': {
    h1: 'HPLC columns',
    title: 'HPLC columns — Waters, Agilent, Shimadzu and others | OGK-CHEM',
    description: 'HPLC and UHPLC columns: C18, C8, Phenyl, HILIC. Filter by length, diameter, particle size and pH. Request a quotation.',
    intro: 'HPLC and UHPLC columns. Filter by phase, length, inner diameter, particle size and working pH range.',
    delivery: DELIVERY_GENERAL,
    faq: [
      ...FAQ_COMMON,
      {
        q: 'Can you help choose a column for my method?',
        a: 'Yes. Describe the method or send the pharmacopoeial monograph and our specialist will suggest a column and a compatible guard column.',
      },
    ],
    documents: DOCS,
    related: [
      { label: 'Guard columns', href: '/catalog/chromatography/precolumns/' },
      { label: 'Filters', href: '/catalog/chromatography/filters/' },
      ...RELATED_SERVICES,
    ],
  },
  'chromatography/filters': {
    h1: 'Chromatography filters',
    title: 'Filters for HPLC and chromatography — OGK-CHEM',
    description: 'PTFE, Nylon, PVDF, PES and RC syringe filters for HPLC sample preparation. Request a quotation.',
    intro: 'Syringe filters for sample preparation: PTFE, Nylon, PVDF, PES and RC membranes.',
    delivery: DELIVERY_GENERAL,
    faq: FAQ_COMMON,
    documents: DOCS,
    related: [{ label: 'HPLC columns', href: '/catalog/chromatography/hplc-columns/' }],
  },
  'chromatography/precolumns': {
    h1: 'HPLC guard columns',
    title: 'Guard columns for HPLC and chromatography — OGK-CHEM',
    description: 'Guard columns and guard cartridges for HPLC and UHPLC columns. Request a quotation.',
    intro: 'Guard columns and cartridges extend the lifetime of the analytical column.',
    delivery: DELIVERY_GENERAL,
    faq: FAQ_COMMON,
    documents: DOCS,
    related: [{ label: 'HPLC columns', href: '/catalog/chromatography/hplc-columns/' }],
  },
  'chromatography/fittings': {
    h1: 'Chromatography fittings',
    title: 'Fittings and capillaries for HPLC — OGK-CHEM',
    description: 'Fittings, ferrules, unions and capillaries for HPLC systems. Request a quotation.',
    intro: 'Fittings, ferrules, unions and capillaries for HPLC systems.',
    delivery: DELIVERY_GENERAL,
    faq: FAQ_COMMON,
    documents: DOCS,
    related: [{ label: 'HPLC columns', href: '/catalog/chromatography/hplc-columns/' }],
  },
  'reference-drugs': {
    h1: 'Reference medicinal products',
    title: 'Reference medicinal products for research | OGK-CHEM',
    description: 'Supply of reference medicinal products to Russia for research purposes. Request a quotation.',
    intro: 'Reference medicinal products for comparative studies — supplied to Russia for research purposes.',
    delivery: DELIVERY_GENERAL,
    faq: FAQ_COMMON,
    documents: DOCS,
    related: [{ label: 'Supply of medicines for research', href: '/services/research-drug-supply/' }, ...RELATED_SERVICES],
  },
  'biological-standards': {
    h1: 'Microorganisms and biological standards',
    title: 'Microorganisms and biological standards for laboratories | OGK-CHEM',
    description: 'ATCC test strains for microbiological quality control. Cold chain delivery, request a quotation.',
    intro: 'ATCC test strains for microbiological quality control.',
    delivery: DELIVERY_STANDARDS,
    faq: FAQ_COMMON,
    documents: DOCS,
    related: [{ label: 'Cold chain', href: '/services/cold-chain/' }],
  },
  'laboratory-equipment': {
    h1: 'Laboratory equipment',
    title: 'Laboratory equipment for pharmaceutical companies | OGK-CHEM',
    description: 'Shimadzu, Agilent and Waters chromatographs, detectors and spectrophotometers. Supply and import to Russia, request a quotation.',
    intro: 'Chromatography systems, modules and spectrophotometers from leading manufacturers.',
    delivery: DELIVERY_GENERAL,
    faq: FAQ_COMMON,
    documents: DOCS,
    related: [{ label: 'HPLC columns', href: '/catalog/chromatography/hplc-columns/' }, ...RELATED_SERVICES],
  },
  'laboratory-glassware': {
    h1: 'Laboratory glassware and containers',
    title: 'Laboratory glassware and containers — OGK-CHEM',
    description: 'Vials, caps, volumetric flasks and laboratory glassware. Request a quotation.',
    intro: 'Autosampler vials and caps, volumetric flasks, bottles and beakers.',
    delivery: DELIVERY_GENERAL,
    faq: FAQ_COMMON,
    documents: DOCS,
    related: [{ label: 'Chromatography filters', href: '/catalog/chromatography/filters/' }],
  },
  pharmacopeias: {
    h1: 'Pharmacopoeias and reference books',
    title: 'Pharmacopoeias and online pharmacopoeia subscriptions — OGK-CHEM',
    description: 'European Pharmacopoeia, USP–NF, British Pharmacopoeia: print editions and annual online subscriptions. Request a quotation.',
    intro: 'Print editions and annual online pharmacopoeia subscriptions.',
    delivery: DELIVERY_GENERAL,
    faq: FAQ_COMMON,
    documents: DOCS,
    related: [{ label: 'Reference standards', href: '/catalog/reference-standards/' }],
  },
};

/** Контент раздела на английском: набор фильтров — из русской версии */
export const categoryContentEn: Record<string, CategoryContent> = Object.fromEntries(
  Object.entries(en).map(([key, c]) => [key, { ...c, facets: categoryContent[key]?.facets ?? ['brand'] }]),
);

/** SEO-посадочные на английском: тексты по slug посадочной */
export const landingTextEn: Record<string, Pick<SeoLanding, 'name' | 'h1' | 'title' | 'description' | 'intro' | 'seoText' | 'faq' | 'related' | 'delivery' | 'documents'>> = {
  'waters-c18': {
    name: 'Waters C18',
    h1: 'Waters C18 HPLC columns',
    title: 'Waters C18 columns: XBridge, SunFire, Symmetry, ACQUITY | OGK-CHEM',
    description: 'Waters C18 columns for HPLC and UHPLC: XBridge, SunFire, Symmetry, ACQUITY UPLC BEH. Filter by length, diameter and particle size; supplied to order.',
    intro: 'Waters reversed-phase columns with C18 phase for HPLC and UHPLC. Choose length, inner diameter and particle size — or send us your method and we will select a column and guard column.',
    seoText: [
      'C18 is the most widely used phase for reversed-phase chromatography: most pharmacopoeial assay and impurity methods run on it. Waters offers several C18 families that differ in particle material and working pH range.',
      'XBridge C18 on hybrid BEH particles works across pH 1–12 and suits methods with alkaline mobile phases. SunFire C18 and Symmetry C18 are silica-based columns for acidic and neutral conditions. ACQUITY UPLC BEH C18 with 1.7 µm particles is designed for high-pressure UHPLC systems.',
      'If your method specifies a column from another manufacturer, our manager will suggest an equivalent by phase, geometry and selectivity. Check system suitability before replacing a column in a validated method.',
    ],
    delivery: DELIVERY_GENERAL,
    faq: [
      {
        q: 'How does XBridge C18 differ from SunFire C18?',
        a: 'XBridge uses hybrid particles and tolerates pH 1–12; SunFire is silica-based and designed for acidic and neutral conditions. For alkaline mobile phases choose XBridge.',
      },
      {
        q: 'Can I order a guard column with the column?',
        a: 'Yes. Add the column to the cart and note in the comment that you need a compatible VanGuard or Sentry guard column — we will include it in the quotation.',
      },
    ],
    documents: DOCS,
    related: [
      { label: 'Waters products', href: '/brands/waters/' },
      { label: 'Guard columns', href: '/catalog/chromatography/precolumns/' },
      { label: 'Cold chain', href: '/services/cold-chain/' },
    ],
  },
  'agilent-c18': {
    name: 'Agilent C18',
    h1: 'Agilent C18 HPLC columns',
    title: 'Agilent C18 columns: ZORBAX Eclipse Plus, Poroshell 120 | OGK-CHEM',
    description: 'Agilent C18 HPLC columns: ZORBAX Eclipse Plus C18 and Poroshell 120 EC-C18. Filter by length, diameter and particle size; supplied to order.',
    intro: 'Agilent columns with C18 phase: fully porous ZORBAX Eclipse Plus and superficially porous Poroshell 120.',
    seoText: [
      'ZORBAX Eclipse Plus C18 is a versatile column on high-purity silica that is often specified in pharmacopoeial and validated methods. Poroshell 120 EC-C18 uses 2.7 µm solid-core particles: its efficiency approaches that of sub-2 µm columns at lower back pressure, so it can run on a standard HPLC system.',
      'When transferring a method to Poroshell, recalculate flow and gradient for the new column geometry and check system suitability.',
    ],
    delivery: DELIVERY_GENERAL,
    faq: [
      {
        q: 'Is Poroshell 120 suitable for standard HPLC, not UHPLC?',
        a: 'Yes, 2.7 µm columns operate at pressures acceptable for most HPLC systems. Tell us the pressure limit of your instrument and we will select the column length.',
      },
    ],
    documents: DOCS,
    related: [
      { label: 'Agilent products', href: '/brands/agilent/' },
      { label: 'Guard columns', href: '/catalog/chromatography/precolumns/' },
    ],
  },
  'c18-4-6x150': {
    name: 'C18 4.6 × 150 mm',
    h1: 'C18 columns 4.6 × 150 mm',
    title: 'C18 HPLC columns 4.6 × 150 mm — Waters, Agilent, Shimadzu | OGK-CHEM',
    description: 'C18 HPLC columns with 4.6 mm inner diameter and 150 mm length from Waters, Agilent, Shimadzu and Welch. Compare particle size and pH range, request a quotation.',
    intro: 'The classic analytical column format for pharmaceutical analysis. Compare columns from different manufacturers by particle size and working pH range.',
    seoText: [
      'The 4.6 × 150 mm column is one of the most common formats in pharmacopoeial methods and manufacturers’ methods. It runs on any analytical HPLC at about 1 mL/min.',
      'Particle size determines efficiency and pressure: 5 µm is standard for older methods, while 3–3.5 µm gives narrower peaks at higher pressure. If your method requires a specific column brand, mention it in your request.',
    ],
    delivery: DELIVERY_GENERAL,
    documents: DOCS,
    related: [
      { label: 'Waters C18 columns', href: '/catalog/chromatography/hplc-columns/waters-c18/' },
      { label: 'Agilent C18 columns', href: '/catalog/chromatography/hplc-columns/agilent-c18/' },
      { label: 'Guard columns', href: '/catalog/chromatography/precolumns/' },
    ],
  },
  phenyl: {
    name: 'Phenyl',
    h1: 'Phenyl HPLC columns',
    title: 'Phenyl HPLC columns — Agilent, Shimadzu | OGK-CHEM',
    description: 'HPLC columns with phenyl phase: alternative selectivity for aromatic compounds. ZORBAX Eclipse XDB-Phenyl, Shim-pack GIST Phenyl. Request a quotation.',
    intro: 'Phenyl-phase columns offer selectivity different from C18 — useful when closely related aromatic compounds do not separate on C18.',
    seoText: [
      'The phenyl phase retains analytes not only through hydrophobic interactions but also through π–π interactions with aromatic rings. The elution order can therefore differ from C18, which helps separate isomers and related impurities.',
      'Phenyl columns are often used as a second, orthogonal column during method development and peak purity confirmation.',
    ],
    delivery: DELIVERY_GENERAL,
    documents: DOCS,
    related: [
      { label: 'All HPLC columns', href: '/catalog/chromatography/hplc-columns/' },
      { label: 'HILIC columns', href: '/catalog/chromatography/hplc-columns/hilic/' },
    ],
  },
  hilic: {
    name: 'HILIC',
    h1: 'HILIC HPLC columns',
    title: 'HILIC columns for chromatography of polar compounds | OGK-CHEM',
    description: 'Hydrophilic interaction chromatography (HILIC) columns retain polar compounds that are poorly retained on C18. Selection and supply to order.',
    intro: 'Hydrophilic interaction (HILIC) columns retain polar analytes that elute with the solvent front in reversed phase.',
    seoText: [
      'HILIC uses a polar stationary phase and a mobile phase rich in acetonitrile. Polar compounds — amino acids, sugars, polar metabolites and counter-ions — are retained more strongly the more polar they are.',
      'A mobile phase with a high organic content suits mass spectrometric detection. HILIC columns need longer equilibration than reversed-phase columns before first use.',
    ],
    delivery: DELIVERY_GENERAL,
    documents: DOCS,
    related: [
      { label: 'All HPLC columns', href: '/catalog/chromatography/hplc-columns/' },
      { label: 'HPLC solvents', href: '/catalog/reagents/' },
    ],
  },
  'labeled-compounds': {
    name: 'Isotope-labelled',
    h1: 'Isotope-labelled reference standards',
    title: 'Isotope-labelled (deuterated) standards for LC-MS | OGK-CHEM',
    description: 'Deuterated and other isotope-labelled compounds — internal standards for quantitative LC-MS/MS. Any pack size on request.',
    intro: 'Isotope-labelled compounds are internal standards for quantitative LC-MS/MS in bioanalysis and impurity control.',
    seoText: [
      'An isotope-labelled internal standard is chemically almost identical to the analyte but differs in mass. It therefore goes through sample preparation and chromatography like the analyte and compensates for losses and matrix effects in mass spectrometric detection.',
      'The custom synthesis manufacturers OGK-CHEM works with supply labelled compounds in any pack size on request: enter the amount and unit in the cart.',
    ],
    delivery: DELIVERY_STANDARDS,
    documents: DOCS,
    related: [
      { label: 'Impurity standards', href: '/catalog/reference-standards/impurity-standards/' },
      { label: 'Substances A–Z', href: '/substances/' },
      { label: 'Cold chain', href: '/services/cold-chain/' },
    ],
  },
};
