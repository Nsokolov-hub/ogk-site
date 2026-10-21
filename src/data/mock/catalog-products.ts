import type { Availability, BrandRef, CardType, FacetKey, Packaging, ProductPreview } from '@/types/catalog';

/**
 * МОКОВЫЙ АССОРТИМЕНТ ДЛЯ ВЁРСТКИ КАТАЛОГА (~460 позиций).
 * Названия веществ и CAS — реальные, каталожные номера и наличие — условные.
 * Заменится выгрузкой ассортимента (ТЗ 9.6). Генерация детерминированная: одинаковый результат на сервере и в браузере.
 */

// ── детерминированный генератор случайных чисел ──
function mulberry32(seed: number) {
  let a = seed;
  return () => {
    a |= 0;
    a = (a + 0x6d2b79f5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}
const rand = mulberry32(20261021);
const chance = (p: number) => rand() < p;
const pick = <T,>(arr: readonly T[]) => arr[Math.floor(rand() * arr.length)];
const digits = (n: number) => Array.from({ length: n }, () => Math.floor(rand() * 10)).join('');

// ── бренды ──
const brand = (slug: string, name: string): BrandRef => ({ slug, name, logo: `/images/brands/${slug}.svg` });
const B = {
  edqm: brand('edqm', 'EDQM'),
  usp: brand('usp', 'USP'),
  bp: { slug: 'british-pharmacopoeia', name: 'British Pharmacopoeia' } as BrandRef,
  lgc: brand('lgc', 'LGC'),
  merck: brand('merck', 'Merck'),
  synzeal: brand('synzeal', 'SynZeal'),
  clearsynth: brand('clearsynth', 'Clearsynth'),
  trc: { slug: 'trc', name: 'TRC' } as BrandRef,
  aozeal: brand('aozeal', 'Aozeal'),
  bioorganics: brand('bioorganics', 'BioOrganics'),
  waters: brand('waters', 'Waters'),
  agilent: brand('agilent', 'Agilent'),
  shimadzu: { slug: 'shimadzu', name: 'Shimadzu' } as BrandRef,
  welch: brand('welch', 'Welch'),
  macklin: brand('macklin', 'Macklin'),
  atcc: { slug: 'atcc', name: 'ATCC' } as BrandRef,
  dwk: { slug: 'dwk', name: 'DWK Life Sciences' } as BrandRef,
  various: { slug: 'various', name: 'Разные производители' } as BrandRef,
};

// ── фасовки: ключ для фильтра + подпись ──
type PackDef = { key: string; label: string };
const pk = (key: string, label: string): PackDef => ({ key, label });
const PK = {
  mg10: pk('10-mg', '10 мг'),
  mg20: pk('20-mg', '20 мг'),
  mg25: pk('25-mg', '25 мг'),
  mg50: pk('50-mg', '50 мг'),
  mg100: pk('100-mg', '100 мг'),
  mg200: pk('200-mg', '200 мг'),
  mg500: pk('500-mg', '500 мг'),
  g1: pk('1-g', '1 г'),
  g25: pk('25-g', '25 г'),
  g100: pk('100-g', '100 г'),
  g500: pk('500-g', '500 г'),
  ml100: pk('100-ml', '100 мл'),
  l1: pk('1-l', '1 л'),
  l25: pk('2-5-l', '2,5 л'),
  pcs1: pk('1-pcs', '1 шт.'),
  pcs100: pk('100-pcs', '100 шт.'),
  vial: pk('1-vial', '1 ампула'),
};

// ── сборка позиции ──
const usedSlugs = new Set<string>();
const slugify = (s: string) =>
  s
    .toLowerCase()
    .replace(/µ/g, 'u')
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '');

let seq = 0;

function make(o: {
  brand: BrandRef;
  name: string;
  catalogNumber: string;
  cas?: string;
  category: [string, string?];
  cardType: CardType;
  packs: PackDef[];
  custom?: boolean;
  inStockChance?: number;
  attrs?: Partial<Record<FacetKey, string[]>>;
}): ProductPreview {
  seq += 1;
  const id = `c${seq}`;
  let slug = `${o.brand.slug}-${slugify(o.catalogNumber)}-${slugify(o.name)}`.slice(0, 80).replace(/-+$/, '');
  if (usedSlugs.has(slug)) slug = `${slug}-${seq}`;
  usedSlugs.add(slug);

  const inStock = chance(o.inStockChance ?? 0.2);
  const packagings: Packaging[] = o.packs.map((p, i) => ({
    id: `${id}-${p.key}`,
    label: p.label,
    availability: (inStock && i === 0 ? 'in_stock' : 'on_request') as Availability,
  }));
  const availability: Availability = inStock ? 'in_stock' : 'on_request';
  const [top, sub] = o.category;

  return {
    id,
    slug,
    cardType: o.cardType,
    name: o.name,
    brand: o.brand,
    catalogNumber: o.catalogNumber,
    cas: o.cas,
    categorySlug: sub ? `${top}/${sub}` : top,
    packagings,
    customPackaging: !!o.custom,
    availability,
    popularity: Math.round(rand() * 1000),
    attributes: {
      brand: [o.brand.slug],
      availability: [availability],
      pack: [...o.packs.map((p) => p.key), ...(o.custom ? ['custom'] : [])],
      ...o.attrs,
    },
  };
}

// ── стандартные образцы ──
const SUBSTANCES: [string, string][] = [
  ['Paracetamol', '103-90-2'],
  ['Ibuprofen', '15687-27-1'],
  ['Caffeine', '58-08-2'],
  ['Carbamazepine', '298-46-4'],
  ['Oxcarbazepine', '28721-07-5'],
  ['Metformin Hydrochloride', '1115-70-4'],
  ['Omeprazole', '73590-58-6'],
  ['Diclofenac Sodium', '15307-79-6'],
  ['Amlodipine Besilate', '111470-99-6'],
  ['Atorvastatin Calcium', '134523-03-8'],
  ['Simvastatin', '79902-63-9'],
  ['Losartan Potassium', '124750-99-8'],
  ['Ciprofloxacin', '85721-33-1'],
  ['Amoxicillin Trihydrate', '61336-70-7'],
  ['Acetylsalicylic Acid', '50-78-2'],
  ['Ketoprofen', '22071-15-4'],
  ['Naproxen', '22204-53-1'],
  ['Lidocaine', '137-58-6'],
  ['Prednisolone', '50-24-8'],
  ['Hydrocortisone', '50-23-7'],
  ['Dexamethasone', '50-02-2'],
  ['Furosemide', '54-31-9'],
  ['Captopril', '62571-86-2'],
  ['Enalapril Maleate', '76095-16-4'],
  ['Clopidogrel Hydrogen Sulfate', '120202-66-6'],
  ['Warfarin', '81-81-2'],
  ['Fluconazole', '86386-73-4'],
  ['Metronidazole', '443-48-1'],
  ['Valsartan', '137862-53-4'],
  ['Sildenafil Citrate', '171599-83-0'],
  ['Gabapentin', '60142-96-3'],
  ['Levetiracetam', '102767-28-2'],
  ['Lamotrigine', '84057-84-1'],
  ['Sertraline Hydrochloride', '79559-97-0'],
  ['Cetirizine Dihydrochloride', '83881-52-1'],
  ['Loratadine', '79794-75-5'],
  ['Montelukast Sodium', '151767-02-1'],
  ['Rosuvastatin Calcium', '147098-20-2'],
  ['Glibenclamide', '10238-21-8'],
  ['Allopurinol', '315-30-0'],
  ['Azithromycin', '83905-01-5'],
  ['Clarithromycin', '81103-11-9'],
  ['Indometacin', '53-86-1'],
  ['Meloxicam', '71125-38-7'],
  ['Nifedipine', '21829-25-4'],
  ['Verapamil Hydrochloride', '152-11-4'],
  ['Propranolol Hydrochloride', '318-98-9'],
  ['Atenolol', '29122-68-7'],
  ['Bisoprolol Fumarate', '104344-23-2'],
  ['Spironolactone', '52-01-7'],
  ['Hydrochlorothiazide', '58-93-5'],
  ['Fluoxetine Hydrochloride', '56296-78-7'],
  ['Pantoprazole Sodium Sesquihydrate', '164579-32-2'],
  ['Tamoxifen Citrate', '54965-24-1'],
];

const STORAGE = ['room', '2-8', '-20'] as const;
const IMPURITY_BRANDS = [B.synzeal, B.clearsynth, B.trc, B.aozeal, B.bioorganics];
const letter = (name: string) => name[0].toUpperCase();
const RS = 'reference-standards';

const standards: ProductPreview[] = [];
SUBSTANCES.forEach(([name, cas]) => {
  const storage = [pick(STORAGE)];
  const apiAttrs = { storage, purpose: chance(0.5) ? ['assay', 'identification'] : ['assay'], type: ['api'] };

  if (chance(0.85))
    standards.push(
      make({
        brand: B.edqm, name: `${name} CRS`, catalogNumber: `${letter(name)}${digits(7)}`, cas,
        category: [RS, 'edqm'], cardType: 'standard', packs: [pick([PK.mg20, PK.mg100, PK.mg200])], attrs: apiAttrs,
      }),
    );
  if (chance(0.75))
    standards.push(
      make({
        brand: B.usp, name: `${name} Reference Standard`, catalogNumber: `1${digits(6)}`, cas,
        category: [RS, 'usp'], cardType: 'standard', packs: [pick([PK.mg100, PK.mg200, PK.mg500])], attrs: apiAttrs,
      }),
    );
  if (chance(0.4))
    standards.push(
      make({
        brand: B.bp, name: `${name} BPCRS`, catalogNumber: `BP${digits(3)}`, cas,
        category: [RS, 'british-pharmacopoeia'], cardType: 'standard', packs: [PK.mg100], attrs: apiAttrs,
      }),
    );
  if (chance(0.4))
    standards.push(
      make({
        brand: B.lgc, name, catalogNumber: `MM${digits(4)}.00`, cas,
        category: [RS, 'lgc'], cardType: 'standard', packs: [PK.mg10, PK.mg25, PK.mg50, PK.mg100], attrs: apiAttrs,
      }),
    );
  if (chance(0.5))
    standards.push(
      make({
        brand: B.merck, name: `${name}, Pharmaceutical Secondary Standard; Certified Reference Material`,
        catalogNumber: `PHR${digits(4)}`, cas, category: [RS, 'merck'], cardType: 'standard',
        packs: pick([[PK.mg500], [PK.g1], [PK.mg500, PK.g1]]), attrs: { ...apiAttrs, purpose: ['assay', 'system-suitability'] },
      }),
    );
  // примеси и меченые соединения — синтезаторы делают любую фасовку под запрос (ТЗ 5.2.2)
  if (chance(0.55)) {
    const n = 1 + Math.floor(rand() * 3);
    for (let i = 0; i < n; i++) {
      const b = pick(IMPURITY_BRANDS);
      const prefix = b === B.synzeal ? 'SZ-' : b === B.clearsynth ? 'CS-' : b === B.aozeal ? 'AZ' : b === B.bioorganics ? 'BO-' : '';
      standards.push(
        make({
          brand: b, name: `${name} EP Impurity ${'ABCDEFG'[i]}`, catalogNumber: `${prefix}${letter(name)}${digits(5)}`,
          category: [RS, 'impurity-standards'], cardType: 'standard', packs: [PK.mg10, PK.mg25, PK.mg50], custom: true,
          inStockChance: 0.08, attrs: { storage: [pick(['2-8', '-20'] as const)], purpose: ['impurity-control'], type: ['impurity'] },
        }),
      );
    }
  }
  if (chance(0.2))
    standards.push(
      make({
        brand: B.trc, name: `${name}-d4`, catalogNumber: `${letter(name)}${digits(6)}`,
        category: [RS, 'impurity-standards'], cardType: 'standard', packs: [PK.mg10, PK.mg25], custom: true, inStockChance: 0.05,
        attrs: { storage: ['-20'], purpose: ['assay'], type: ['labeled'] },
      }),
    );
});

// ── хроматография ──
const CH = 'chromatography';
type ColumnFamily = { brand: BrandRef; name: string; phase: string; ph: string; particles: number[]; diameters: number[]; pn: () => string };
const FAMILIES: ColumnFamily[] = [
  { brand: B.waters, name: 'XBridge C18', phase: 'C18', ph: '1-12', particles: [3.5, 5], diameters: [2.1, 4.6], pn: () => `186${digits(6)}` },
  { brand: B.waters, name: 'XBridge C8', phase: 'C8', ph: '1-12', particles: [3.5, 5], diameters: [4.6], pn: () => `186${digits(6)}` },
  { brand: B.waters, name: 'SunFire C18', phase: 'C18', ph: '2-8', particles: [3.5, 5], diameters: [4.6], pn: () => `186${digits(6)}` },
  { brand: B.waters, name: 'Symmetry C18', phase: 'C18', ph: '2-7', particles: [3.5, 5], diameters: [3.9, 4.6], pn: () => `WAT${digits(6)}` },
  { brand: B.waters, name: 'ACQUITY UPLC BEH C18', phase: 'C18', ph: '1-12', particles: [1.7], diameters: [2.1], pn: () => `186${digits(6)}` },
  { brand: B.agilent, name: 'ZORBAX Eclipse Plus C18', phase: 'C18', ph: '2-9', particles: [3.5, 5], diameters: [3, 4.6], pn: () => `959${digits(3)}-${digits(3)}` },
  { brand: B.agilent, name: 'ZORBAX SB-C8', phase: 'C8', ph: '1-8', particles: [3.5, 5], diameters: [4.6], pn: () => `883${digits(3)}-${digits(3)}` },
  { brand: B.agilent, name: 'Poroshell 120 EC-C18', phase: 'C18', ph: '2-8', particles: [2.7], diameters: [2.1, 3, 4.6], pn: () => `69${digits(4)}-${digits(3)}` },
  { brand: B.agilent, name: 'ZORBAX Eclipse XDB-Phenyl', phase: 'Phenyl', ph: '2-9', particles: [5], diameters: [4.6], pn: () => `993${digits(3)}-${digits(3)}` },
  { brand: B.shimadzu, name: 'Shim-pack GIST C18', phase: 'C18', ph: '1-10', particles: [3, 5], diameters: [2.1, 4.6], pn: () => `227-${digits(5)}-${digits(2)}` },
  { brand: B.shimadzu, name: 'Shim-pack GIST Phenyl', phase: 'Phenyl', ph: '1-10', particles: [3, 5], diameters: [4.6], pn: () => `227-${digits(5)}-${digits(2)}` },
  { brand: B.welch, name: 'Ultimate XB-C18', phase: 'C18', ph: '1.5-10', particles: [3, 5], diameters: [2.1, 4.6], pn: () => `00201-${digits(5)}` },
  { brand: B.welch, name: 'Ultimate AQ-C18', phase: 'C18', ph: '1.5-8', particles: [3, 5], diameters: [4.6], pn: () => `00205-${digits(5)}` },
  { brand: B.welch, name: 'Ultimate HILIC Amide', phase: 'HILIC', ph: '2-8', particles: [3, 5], diameters: [2.1, 4.6], pn: () => `00217-${digits(5)}` },
];
const LENGTHS = [50, 100, 150, 250];
const num = (n: number) => String(n).replace('.', ',');

const chromatography: ProductPreview[] = [];
FAMILIES.forEach((f) => {
  const combos = new Set<string>();
  const want = 4 + Math.floor(rand() * 4);
  for (let i = 0; i < want * 3 && combos.size < want; i++) {
    const length = f.particles[0] === 1.7 ? pick([50, 100, 150]) : pick(LENGTHS);
    const d = pick(f.diameters);
    const p = pick(f.particles);
    const key = `${length}-${d}-${p}`;
    if (combos.has(key)) continue;
    combos.add(key);
    chromatography.push(
      make({
        brand: f.brand, name: `${f.name} Column, ${num(p)} µm, ${num(d)} × ${length} mm`, catalogNumber: f.pn(),
        category: [CH, 'hplc-columns'], cardType: 'equipment', packs: [PK.pcs1], inStockChance: 0.3,
        attrs: { phase: [f.phase], length: [String(length)], diameter: [String(d)], particle: [String(p)], ph: [f.ph] },
      }),
    );
  }
});
// предколонки
[
  [B.waters, 'XBridge C18 VanGuard Cartridge, 3.5 µm, 3.9 × 5 mm', 'C18', '1-12'],
  [B.waters, 'ACQUITY UPLC BEH C18 VanGuard Pre-column, 1.7 µm, 2.1 × 5 mm', 'C18', '1-12'],
  [B.agilent, 'ZORBAX Eclipse Plus C18 Guard Cartridge, 5 µm, 4.6 × 12.5 mm', 'C18', '2-9'],
  [B.agilent, 'InfinityLab Poroshell 120 EC-C18 Fast Guard, 2.7 µm, 4.6 × 5 mm', 'C18', '2-8'],
  [B.welch, 'Ultimate XB-C18 Guard Cartridge, 5 µm, 4.6 × 10 mm', 'C18', '1.5-10'],
  [B.welch, 'Ultimate HILIC Amide Guard Cartridge, 5 µm, 4.6 × 10 mm', 'HILIC', '2-8'],
  [B.shimadzu, 'Shim-pack GIST C18 Guard Cartridge, 5 µm, 4.0 × 10 mm', 'C18', '1-10'],
  [B.waters, 'SunFire C18 Sentry Guard Cartridge, 5 µm, 4.6 × 20 mm', 'C18', '2-8'],
].forEach(([b, name, phase, ph]) =>
  chromatography.push(
    make({
      brand: b as BrandRef, name: name as string, catalogNumber: `${(b as BrandRef).slug === 'agilent' ? '820950-' : '186'}${digits(3)}`,
      category: [CH, 'precolumns'], cardType: 'equipment', packs: [pick([PK.pcs1, pk('2-pcs', '2 шт.'), pk('3-pcs', '3 шт.')])],
      attrs: { phase: [phase as string], ph: [ph as string] },
    }),
  ),
);
// фильтры
['PTFE', 'Nylon', 'PVDF', 'PES', 'RC'].forEach((membrane) =>
  ['0,22', '0,45'].forEach((pore) =>
    [13, 25].forEach((d) => {
      if (!chance(0.7)) return;
      const b = pick([B.agilent, B.welch, B.waters]);
      chromatography.push(
        make({
          brand: b, name: `Syringe Filter, ${membrane}, ${pore} µm, ${d} mm`, catalogNumber: `${b === B.agilent ? '5190-' : 'SF-'}${digits(4)}`,
          category: [CH, 'filters'], cardType: 'equipment', packs: [PK.pcs100], inStockChance: 0.4,
        }),
      );
    }),
  ),
);
// фитинги
['PEEK Finger-tight Fitting, 1/16"', 'Stainless Steel Ferrule, 1/16"', 'Zero Dead Volume Union, 1/16"', 'PEEK Tubing, 0.13 mm ID, 5 m', 'Stainless Steel Capillary, 0.12 × 150 mm', 'Column Coupler, 1/16"']
  .forEach((name) => {
    const b = pick([B.agilent, B.waters]);
    chromatography.push(
      make({
        brand: b, name, catalogNumber: `${b === B.agilent ? '5067-' : '700'}${digits(4)}`,
        category: [CH, 'fittings'], cardType: 'equipment', packs: [pick([PK.pcs1, pk('10-pcs', '10 шт.')])], inStockChance: 0.35,
      }),
    );
  });

// ── реактивы ──
const REAGENTS: [string, string, 'solvent' | 'solid' | 'acid'][] = [
  ['Acetonitrile, gradient grade for liquid chromatography', '75-05-8', 'solvent'],
  ['Methanol, gradient grade for liquid chromatography', '67-56-1', 'solvent'],
  ['Water for chromatography (LC-MS Grade)', '7732-18-5', 'solvent'],
  ['2-Propanol, for liquid chromatography', '67-63-0', 'solvent'],
  ['Ethanol absolute, for analysis', '64-17-5', 'solvent'],
  ['n-Hexane, for liquid chromatography', '110-54-3', 'solvent'],
  ['n-Heptane, for liquid chromatography', '142-82-5', 'solvent'],
  ['Tetrahydrofuran, for liquid chromatography', '109-99-9', 'solvent'],
  ['Dichloromethane, for liquid chromatography', '75-09-2', 'solvent'],
  ['Ethyl acetate, for liquid chromatography', '141-78-6', 'solvent'],
  ['Acetone, for analysis', '67-64-1', 'solvent'],
  ['Toluene, for analysis', '108-88-3', 'solvent'],
  ['Dimethyl sulfoxide, for analysis', '67-68-5', 'solvent'],
  ['Triethylamine, for synthesis', '121-44-8', 'solvent'],
  ['Trifluoroacetic acid, for HPLC', '76-05-1', 'acid'],
  ['Formic acid, for LC-MS', '64-18-6', 'acid'],
  ['Acetic acid (glacial), for analysis', '64-19-7', 'acid'],
  ['ortho-Phosphoric acid 85%, for analysis', '7664-38-2', 'acid'],
  ['Hydrochloric acid 37%, for analysis', '7647-01-0', 'acid'],
  ['Potassium dihydrogen phosphate, for analysis', '7778-77-0', 'solid'],
  ['Ammonium acetate, for LC-MS', '631-61-8', 'solid'],
  ['Ammonium formate, for LC-MS', '540-69-2', 'solid'],
  ['Sodium acetate anhydrous, for analysis', '127-09-3', 'solid'],
  ['Sodium hydroxide pellets, for analysis', '1310-73-2', 'solid'],
  ['Sodium chloride, for analysis', '7647-14-5', 'solid'],
  ['Potassium chloride, for analysis', '7447-40-7', 'solid'],
  ['Methyl orange (C.I. 13025), indicator', '547-58-0', 'solid'],
  ['Phenolphthalein, indicator', '77-09-8', 'solid'],
];
const reagents: ProductPreview[] = [];
REAGENTS.forEach(([name, cas, kind]) => {
  const brands = chance(0.5) ? [B.merck, B.macklin] : [pick([B.merck, B.macklin])];
  brands.forEach((b) =>
    reagents.push(
      make({
        brand: b, name, cas, catalogNumber: b === B.merck ? `1.${digits(5)}` : `${letter(name)}${digits(6)}`,
        category: ['reagents'], cardType: 'standard', inStockChance: 0.35,
        packs: kind === 'solid' ? [PK.g100, PK.g500] : kind === 'acid' ? [PK.ml100, PK.l1] : [PK.l1, PK.l25],
        attrs: { storage: ['room'] },
      }),
    ),
  );
});

// ── прочее: препараты, штаммы, оборудование, посуда, фармакопеи ──
const other: ProductPreview[] = [];
['Metformin 500 mg, film-coated tablets', 'Amlodipine 10 mg, tablets', 'Atorvastatin 20 mg, film-coated tablets', 'Omeprazole 20 mg, gastro-resistant capsules', 'Ibuprofen 400 mg, film-coated tablets', 'Valsartan 160 mg, film-coated tablets']
  .forEach((name) =>
    other.push(
      make({
        brand: B.various, name, catalogNumber: `RD-${digits(5)}`, category: ['reference-drugs'], cardType: 'other',
        packs: [pk('1-pack', '1 упаковка')], inStockChance: 0.05, attrs: { storage: ['room'] },
      }),
    ),
  );
[
  ['Escherichia coli (Migula) Castellani and Chalmers', '25922'],
  ['Escherichia coli (Migula) Castellani and Chalmers', '8739'],
  ['Staphylococcus aureus subsp. aureus Rosenbach', '25923'],
  ['Staphylococcus aureus subsp. aureus Rosenbach', '6538'],
  ['Pseudomonas aeruginosa (Schroeter) Migula', '27853'],
  ['Pseudomonas aeruginosa (Schroeter) Migula', '9027'],
  ['Candida albicans (Robin) Berkhout', '10231'],
  ['Aspergillus brasiliensis Varga et al.', '16404'],
  ['Bacillus subtilis subsp. spizizenii Nakamura et al.', '6633'],
  ['Salmonella enterica subsp. enterica serovar Typhimurium', '14028'],
].forEach(([name, code]) =>
  other.push(
    make({
      brand: B.atcc, name: `${name}, lyophilized`, catalogNumber: code, category: ['biological-standards'], cardType: 'other',
      packs: [PK.vial], inStockChance: 0.1, attrs: { storage: [pick(['2-8', '-80'] as const)] },
    }),
  ),
);
[
  [B.shimadzu, 'UV-1900i UV-Vis Spectrophotometer'],
  [B.shimadzu, 'LC-2050C 3D Integrated HPLC System'],
  [B.agilent, '1260 Infinity II Quaternary Pump'],
  [B.agilent, '1260 Infinity II Diode Array Detector WR'],
  [B.waters, 'Alliance e2695 Separations Module'],
  [B.waters, '2998 Photodiode Array Detector'],
].forEach(([b, name]) =>
  other.push(
    make({
      brand: b as BrandRef, name: name as string, catalogNumber: `${(b as BrandRef).slug.toUpperCase().slice(0, 2)}-${digits(6)}`,
      category: ['laboratory-equipment'], cardType: 'equipment', packs: [PK.pcs1], inStockChance: 0.05,
    }),
  ),
);
[
  [B.agilent, 'Screw Top Vial, 2 mL, amber, write-on spot', pk('100-pcs', '100 шт.')],
  [B.agilent, 'Screw Cap, PTFE/silicone septa, 9 mm', pk('100-pcs', '100 шт.')],
  [B.waters, 'TruView LCMS Certified Vial, 2 mL, clear', pk('100-pcs', '100 шт.')],
  [B.dwk, 'DURAN Volumetric Flask, class A, 10 mL', PK.pcs1],
  [B.dwk, 'DURAN Volumetric Flask, class A, 50 mL', PK.pcs1],
  [B.dwk, 'DURAN Volumetric Flask, class A, 100 mL', PK.pcs1],
  [B.dwk, 'DURAN Laboratory Bottle with GL 45 cap, 500 mL', PK.pcs1],
  [B.dwk, 'DURAN Beaker, low form, 250 mL', PK.pcs1],
].forEach(([b, name, pack]) =>
  other.push(
    make({
      brand: b as BrandRef, name: name as string, catalogNumber: `${digits(4)}-${digits(4)}`,
      category: ['laboratory-glassware'], cardType: 'other', packs: [pack as PackDef], inStockChance: 0.4,
    }),
  ),
);
[
  [B.edqm, 'European Pharmacopoeia 11th Edition, online subscription (1 year)'],
  [B.edqm, 'European Pharmacopoeia 11th Edition, print'],
  [B.usp, 'USP–NF Online, annual subscription'],
  [B.bp, 'British Pharmacopoeia 2026, print + online'],
  [B.bp, 'British Pharmacopoeia 2026, online subscription (1 year)'],
].forEach(([b, name]) =>
  other.push(
    make({
      brand: b as BrandRef, name: name as string, catalogNumber: `PH-${digits(5)}`, category: ['pharmacopeias'], cardType: 'other',
      packs: [PK.pcs1], inStockChance: 0.1,
    }),
  ),
);

export const catalogProducts: ProductPreview[] = [...standards, ...chromatography, ...reagents, ...other];
