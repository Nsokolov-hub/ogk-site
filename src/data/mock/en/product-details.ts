import type { DocumentType, SpecRow, Substance } from '@/types/catalog';
import type { Faq } from '@/types/content';

/**
 * Английские тексты карточек и субстанций (EN-04). Химические данные (CAS, формула, масса) общие — в русских моках;
 * здесь только то, что пишется словами. Ключ — slug товара или субстанции.
 */

export interface ProductEnrichmentEn {
  description: string[];
  monograph?: string;
  specs?: SpecRow[];
  /** Названия документов — по порядку документов карточки */
  documents?: string[];
  faq?: Faq[];
}

/** Подписи документов по типу — когда у документа нет своего английского названия */
export const DOCUMENT_TITLES_EN: Record<DocumentType, string> = {
  coa: 'Certificate of analysis (CoA)',
  sds: 'Safety data sheet (SDS)',
  spec: 'Specification',
  datasheet: 'Datasheet',
  manual: 'Instructions for use',
  certificate: 'Manufacturer certificate',
  'strain-passport': 'Strain product sheet',
  leaflet: 'Leaflet',
};

const FAQ_CRS: Faq = {
  q: 'Why is there no expiry date on the pharmacopoeial standard label?',
  a: 'Pharmacopoeial organisations confirm batch suitability through their current catalogue: a batch may be used while it is listed as current. We check the batch status before shipment and state it in the quotation.',
};

const FAQ_COA: Faq = {
  q: 'Can I get a certificate of analysis for a specific batch?',
  a: 'Yes. Click “Request batch CoA” and we will send the document with the quotation or after shipment.',
};

export const productEnrichmentEn: Record<string, ProductEnrichmentEn> = {
  'edqm-y0001897-oxcarbazepine-crs': {
    monograph: 'Ph. Eur., monograph “Oxcarbazepine”',
    description: [
      'Oxcarbazepine CRS is a European Pharmacopoeia chemical reference standard (EDQM) for testing oxcarbazepine substance and dosage forms. It is used in the tests where the Ph. Eur. monograph specifies it: identification and HPLC assay.',
      'A pharmacopoeial standard does not come with a conventional certificate showing numerical purity: where a value is needed for calculation, it is given in the manufacturer’s leaflet, and batch suitability is confirmed by the current EDQM catalogue. We check the batch status before shipment and state it in the quotation.',
      'Store at +2…+8 °C in the original container; we ship it in an insulated box with coolant packs and temperature monitoring. For related compounds testing, we will select oxcarbazepine impurity standards from EDQM and custom synthesis manufacturers — they are listed on the substance page.',
    ],
    documents: ['EDQM leaflet', 'Safety data sheet (SDS)', 'Current batch confirmation'],
    faq: [
      FAQ_CRS,
      {
        q: 'How does this standard differ from a Merck secondary standard?',
        a: 'The EDQM pharmacopoeial standard is primary: it is used in tests according to the Ph. Eur. monograph. A secondary standard is traceable to the primary one and is cheaper for routine control. The choice depends on the document you are testing against.',
      },
    ],
  },
  'edqm-p0300000-paracetamol-crs': {
    monograph: 'Ph. Eur., monograph “Paracetamol”',
    description: [
      'Paracetamol CRS is a European Pharmacopoeia chemical reference standard for testing paracetamol substance and medicinal products containing it. It is used in the tests where the Ph. Eur. monograph specifies it: identification, assay and chromatographic system suitability.',
      'Batch suitability is confirmed by the current EDQM catalogue; the manufacturer supplies a leaflet with conditions of use. We check the batch status before shipment and state it in the quotation.',
      'For paracetamol impurity testing, including 4-aminophenol, we will select impurity standards from different manufacturers — see the substance page.',
    ],
    documents: ['EDQM leaflet', 'Safety data sheet (SDS)'],
    faq: [FAQ_CRS],
  },
  'usp-1100000-carbamazepine-reference-standard': {
    monograph: 'USP–NF, monograph “Carbamazepine”',
    description: [
      'Carbamazepine Reference Standard is a United States Pharmacopeia reference standard (USP RS) for tests according to USP–NF monographs for carbamazepine substance and dosage forms: identification, assay and system suitability.',
      'USP confirms lot suitability through its catalogue: a lot may be used while it is listed as current. We check the lot status before shipment. Store and ship at room temperature in the original container.',
      'If you test according to the European Pharmacopoeia, you need an EDQM standard; for impurity control — carbamazepine impurity standards such as 10,11-dihydrocarbamazepine. All of them are listed on the substance page.',
    ],
    documents: ['Safety data sheet (SDS)', 'Current lot information'],
    faq: [FAQ_CRS],
  },
  'lgc-mm0080-02-10-11-dihydrocarbamazepine': {
    description: [
      '10,11-Dihydrocarbamazepine is a related impurity of carbamazepine specified by the European Pharmacopoeia as impurity A. The standard is used to identify the impurity peak, check resolution and validate HPLC methods for related substances.',
      'LGC supplies the standard in several fixed pack sizes — choose the one you need in the table below. Each batch comes with the manufacturer’s certificate of analysis confirming identity and purity.',
      'To build a complete set for carbamazepine impurity control, open the substance page: it lists API and impurity standards from all manufacturers, and you can add them to the cart in one action.',
    ],
    documents: ['Certificate of analysis (sample)', 'Safety data sheet (SDS)'],
    faq: [FAQ_COA],
  },
  'synzeal-sz-o004004-omeprazole-sulfone': {
    description: [
      'Omeprazole sulfone is an oxidation product of omeprazole specified by the European Pharmacopoeia as impurity D. The standard is needed to identify the impurity peak and validate HPLC methods for related substances of omeprazole and esomeprazole.',
      'SynZeal synthesises impurity standards to order, so in addition to standard pack sizes you can order any quantity: choose “Custom pack size” and enter the amount in milligrams. We state the synthesis time and accompanying data (CoA, spectra) in the quotation.',
      'Store at +2…+8 °C protected from light. Other omeprazole impurities are listed on the substance page.',
    ],
    documents: ['Certificate of analysis (sample)', 'Safety data sheet (SDS)'],
    faq: [
      {
        q: 'Can I order 5 mg or 100 mg?',
        a: 'Yes. Choose “Custom pack size” and enter the quantity — the manufacturer will prepare it to order. We will state the lead time in the quotation.',
      },
      FAQ_COA,
    ],
  },
  'waters-186003116-xbridge-c18-column': {
    specs: [
      { label: 'Phase', value: 'C18, hybrid BEH particles' },
      { label: 'Particle size', value: '5 µm' },
      { label: 'Pore size', value: '130 Å' },
      { label: 'Inner diameter × length', value: '4.6 × 150 mm' },
      { label: 'pH range', value: '1–12' },
      { label: 'USP classification', value: 'L1' },
      { label: 'Compatibility', value: 'HPLC systems with standard 10-32 fittings' },
      { label: 'Contents', value: 'Column, manufacturer certificate, care and use manual' },
    ],
    description: [
      'XBridge C18 is a Waters column packed with ethylene-bridged hybrid (BEH) particles. The packing tolerates a wide pH range from 1 to 12, so the column is chosen for high-pH method development, where basic compounds are neutral and give symmetrical peaks.',
      'The 4.6 × 150 mm format with 5 µm particles is a universal choice for pharmacopoeial HPLC methods with L1 phase. The column fits any HPLC system with standard fittings.',
      'To extend column lifetime, use a guard column with the same phase — suitable VanGuard and Sentry cartridges are listed in the compatible accessories block below.',
    ],
    documents: ['Care and Use Manual', 'Column manufacturer certificate'],
    faq: [
      {
        q: 'Will the column suit my method?',
        a: 'Send us the method or its parameters (phase, dimensions, particle size, mobile phase pH) and we will select a Waters column or an equivalent from another manufacturer with the same USP classification.',
      },
    ],
  },
  'agilent-959993-902-zorbax-eclipse-plus-c18': {
    specs: [
      { label: 'Phase', value: 'C18, double end-capped' },
      { label: 'Particle size', value: '5 µm' },
      { label: 'Pore size', value: '95 Å' },
      { label: 'Inner diameter × length', value: '4.6 × 150 mm' },
      { label: 'pH range', value: '2–9' },
      { label: 'USP classification', value: 'L1' },
      { label: 'Contents', value: 'Column, manufacturer certificate' },
    ],
    description: [
      'ZORBAX Eclipse Plus C18 is an Agilent column packed with high-purity, double end-capped silica. It gives symmetrical peaks for basic compounds and suits most pharmacopoeial methods with L1 phase in the pH range 2–9.',
      'The 4.6 × 150 mm, 5 µm format is the classic choice for reversed-phase HPLC and transfers easily between systems and methods. To protect the column we will select an Eclipse Plus C18 guard column with the same phase.',
      'If your method requires pH above 9, consider columns with hybrid particles, such as Waters XBridge C18.',
    ],
    documents: ['Column manufacturer certificate'],
  },
  'atcc-25922-escherichia-coli': {
    specs: [
      { label: 'Strain', value: 'ATCC 25922' },
      { label: 'Species', value: 'Escherichia coli (Migula) Castellani and Chalmers' },
      { label: 'Biosafety level', value: 'BSL-1' },
      { label: 'Supplied as', value: 'Lyophilised culture, 1 vial' },
      { label: 'Storage', value: '+2…+8 °C before rehydration' },
    ],
    description: [
      'Escherichia coli ATCC 25922 is a reference strain that laboratories use for quality control of culture media and antimicrobial susceptibility testing. The strain is supplied lyophilised in a vial.',
      'Importing microorganisms requires documents: we handle customs clearance and, where needed, import permits. Lead times depend on the document package — we will state them in the quotation.',
      'The strain comes with the manufacturer’s product sheet with rehydration and cultivation conditions.',
    ],
    documents: ['Strain product sheet', 'Batch certificate of analysis'],
    faq: [
      {
        q: 'What documents are needed to import the strain?',
        a: 'It depends on the biosafety level and intended use. For BSL-1, the manufacturer’s accompanying documents and a letter on the intended use are usually enough — our foreign trade specialist will confirm the exact list.',
      },
    ],
  },
  'edqm-ph-eur-online-subscription': {
    specs: [
      { label: 'Edition', value: 'Current edition of the European Pharmacopoeia with supplements' },
      { label: 'Format', value: 'Online access' },
      { label: 'Term', value: '1 year' },
      { label: 'Language', value: 'English' },
    ],
    description: [
      'An annual subscription to the online European Pharmacopoeia gives access to the current edition and the supplements published during the subscription term. It is more convenient than print: full-text search and up-to-date monographs without waiting for delivery.',
      'We will arrange the subscription for your organisation: when ordering, specify the number of users and a contact person for activation. The invoice and closing documents are issued by a Russian legal entity.',
      'For other pharmacopoeias — USP–NF or British Pharmacopoeia — see the “Pharmacopoeias and reference books” section.',
    ],
  },
};

/** Описания субстанций на английском; без текста EN-страница субстанции не индексируется */
export const substanceTextEn: Record<string, Pick<Substance, 'synonyms' | 'description'>> = {
  oxcarbazepine: {
    synonyms: ['10-oxo-10,11-dihydro-5H-dibenzo[b,f]azepine-5-carboxamide', 'GP 47680'],
    description: [
      'Oxcarbazepine is an antiepileptic drug, a keto derivative of carbamazepine. In the body it is almost completely converted to the active metabolite, the 10-monohydroxy derivative (licarbazepine), so analytical work with oxcarbazepine needs standards for both the substance and the metabolite.',
      'Quality control of the substance and finished dosage forms uses pharmacopoeial reference standards (EDQM, USP) for identification and assay, and impurity standards for HPLC method validation and related substances control.',
      'This page lists oxcarbazepine, metabolite and impurity standards from all the manufacturers we supply. Select the items you need and add them to the quote cart in one action.',
    ],
  },
  carbamazepine: {
    synonyms: ['5H-dibenzo[b,f]azepine-5-carboxamide'],
    description: [
      'Carbamazepine is an antiepileptic and mood-stabilising drug from the iminostilbene group. The European Pharmacopoeia and the United States Pharmacopeia both have monographs for the substance, so testing against them requires the corresponding pharmacopoeial reference standards.',
      'Control of related impurities uses impurity standards, including 10,11-dihydrocarbamazepine (Ph. Eur. impurity A). Impurity standards from custom synthesis manufacturers are available in any pack size on request.',
      'Below are carbamazepine and impurity standards from different manufacturers. Select the items you need and send one request for all of them.',
    ],
  },
  paracetamol: {
    synonyms: ['Acetaminophen', 'N-(4-hydroxyphenyl)acetamide'],
    description: [
      'Paracetamol (acetaminophen) is an analgesic and antipyretic and one of the most widely used substances in pharmaceutical manufacturing. The European, United States and British pharmacopoeias all have paracetamol monographs.',
      'Tests according to pharmacopoeial monographs use reference standards of the corresponding pharmacopoeia; routine control can use secondary standards traceable to the primary ones. Impurity control, in particular for 4-aminophenol, uses impurity standards.',
      'This page lists paracetamol and impurity standards from all the manufacturers we supply.',
    ],
  },
  omeprazole: {
    synonyms: ['Omeprazole sulfone — Ph. Eur. impurity D'],
    description: [
      'Omeprazole is a proton pump inhibitor and a benzimidazole derivative. The substance is sensitive to acid and light, and its oxidation and degradation products are specified by pharmacopoeias as related impurities.',
      'Omeprazole sulfone (Ph. Eur. impurity D) is one of the main oxidation products; its standard is needed for method validation and impurity control. Custom synthesis manufacturers supply omeprazole impurity standards in any pack size on request.',
      'Below are omeprazole and impurity standards from different manufacturers. Select items and add them to the quote cart.',
    ],
  },
  ibuprofen: {
    synonyms: ['2-[4-(2-methylpropyl)phenyl]propanoic acid'],
    description: [
      'Ibuprofen is a non-steroidal anti-inflammatory drug, a propionic acid derivative. The European Pharmacopoeia and the United States Pharmacopeia both have monographs for the substance.',
      'Identification and assay use pharmacopoeial reference standards; related substances control uses impurity standards. We will select standards for a specific pharmacopoeial monograph or your in-house method.',
      'This page lists ibuprofen and impurity standards from all the manufacturers we supply.',
    ],
  },
  metformin: {
    synonyms: ['Metformin hydrochloride', 'N,N-dimethylimidodicarbonimidic diamide hydrochloride'],
    description: [
      'Metformin is an oral glucose-lowering drug from the biguanide group; dosage forms and reference standards usually use metformin hydrochloride.',
      'Tests according to Ph. Eur. and USP monographs require the corresponding pharmacopoeial reference standards; related impurities control requires impurity standards, including cyanoguanidine.',
      'Below are metformin and impurity standards from different manufacturers.',
    ],
  },
};
