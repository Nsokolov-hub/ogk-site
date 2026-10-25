import type { SeoLanding } from '@/types/content';

/*
 * SEO-посадочные из срезов фильтров (ТЗ URL-07) живут в коде витрины, пока их не начнут вести в админке (ADM-07).
 * Позиции, счётчики и производители срезов приходят из API каталога.
 */

const DELIVERY_STANDARDS = [
  'Поставка под заказ из каталогов производителей — срок указываем в коммерческом предложении',
  'Соблюдаем условия хранения при перевозке: +2…+8 °C, −20 °C, сухой лёд',
  'Сопроводительные документы: сертификат анализа (CoA) партии, паспорт безопасности (SDS)',
  'Доставка в любой регион России, документы для закупок по 44-ФЗ и 223-ФЗ',
];

const DELIVERY_GENERAL = [
  'Поставка под заказ из каталогов производителей — срок указываем в коммерческом предложении',
  'Доставка в любой регион России',
  'Документы для закупок по 44-ФЗ и 223-ФЗ',
];

const DOCS = [
  { title: 'Карточка организации и реквизиты', href: '/files/kartochka.pdf' },
  { title: 'Политика конфиденциальности', href: '/files/politika.pdf' },
];

const RELATED_SERVICES = [
  { label: 'Холодовая цепь', href: '/services/cold-chain/' },
  { label: 'Таможенное оформление', href: '/services/customs-clearance/' },
  { label: 'Разрешения на ввоз', href: '/services/import-permits/' },
];

/**
 * SEO-посадочные из срезов фильтров (ТЗ URL-07). Каждая — отдельный поисковый интент со своими H1, Title и текстом
 * (ТЗ 2: «один интент — одна посадочная, если есть спрос и содержание»). Тексты — черновики, факты проверяет химик.
 * Посадочная индексируется, если в срезе не меньше LANDING_MIN_ITEMS позиций.
 */
export const LANDING_MIN_ITEMS = 3;

const HPLC = 'chromatography/hplc-columns';
const COLUMN_FACETS = ['brand', 'phase', 'length', 'diameter', 'particle', 'ph'] as const;

export const landings: SeoLanding[] = [
  {
    parent: HPLC,
    slug: 'waters-c18',
    name: 'Waters C18',
    preset: { brand: ['waters'], phase: ['C18'] },
    h1: 'Колонки Waters C18 для ВЭЖХ',
    title: 'Колонки Waters C18: XBridge, SunFire, Symmetry, ACQUITY | ОГК-ХИМ',
    description:
      'Колонки Waters C18 для ВЭЖХ и УВЭЖХ: XBridge, SunFire, Symmetry, ACQUITY UPLC BEH. Подбор по длине, диаметру и размеру частиц, поставка под заказ.',
    intro: 'Обращённо-фазовые колонки Waters с фазой C18 для ВЭЖХ и УВЭЖХ. Выберите длину, внутренний диаметр и размер частиц — или пришлите методику, подберём колонку и предколонку.',
    seoText: [
      'C18 — самая распространённая фаза для обращённо-фазовой хроматографии: на ней выполняется большинство фармакопейных методик количественного определения и контроля примесей. У Waters несколько семейств C18, они различаются материалом частиц и рабочим диапазоном pH.',
      'XBridge C18 на гибридных частицах BEH работает в широком диапазоне pH 1–12 и подходит для методик с щелочной подвижной фазой. SunFire C18 и Symmetry C18 — колонки на силикагеле для кислых и нейтральных условий. ACQUITY UPLC BEH C18 с частицами 1,7 мкм рассчитана на системы УВЭЖХ с высоким давлением.',
      'Если в методике указана колонка другого производителя, менеджер предложит эквивалент по фазе, геометрии и селективности. Перед заменой колонки в валидированной методике проверьте пригодность хроматографической системы.',
    ],
    delivery: DELIVERY_GENERAL,
    faq: [
      {
        q: 'Чем XBridge C18 отличается от SunFire C18?',
        a: 'XBridge построена на гибридных частицах и выдерживает pH 1–12, SunFire — на силикагеле и рассчитана на кислые и нейтральные условия. Для щелочных подвижных фаз выбирают XBridge.',
      },
      {
        q: 'Можно ли заказать предколонку к колонке?',
        a: 'Да. Добавьте колонку в корзину и укажите в комментарии, что нужна совместимая предколонка VanGuard или Sentry, — включим её в коммерческое предложение.',
      },
    ],
    documents: DOCS,
    related: [
      { label: 'Продукция Waters', href: '/brands/waters/' },
      { label: 'Предколонки', href: '/catalog/chromatography/precolumns/' },
      { label: 'Как выбрать колонку для ВЭЖХ', href: '/articles/how-to-choose-hplc-column/' },
      ...RELATED_SERVICES.slice(0, 1),
    ],
    facets: [...COLUMN_FACETS],
    updatedAt: '2026-10-22',
  },
  {
    parent: HPLC,
    slug: 'agilent-c18',
    name: 'Agilent C18',
    preset: { brand: ['agilent'], phase: ['C18'] },
    h1: 'Колонки Agilent C18 для ВЭЖХ',
    title: 'Колонки Agilent C18: ZORBAX Eclipse Plus, Poroshell 120 | ОГК-ХИМ',
    description:
      'Колонки Agilent C18 для ВЭЖХ: ZORBAX Eclipse Plus C18 и Poroshell 120 EC-C18. Подбор по длине, диаметру и размеру частиц, поставка под заказ.',
    intro: 'Колонки Agilent с фазой C18: полностью пористые ZORBAX Eclipse Plus и Poroshell 120 с частицами «твёрдое ядро — пористая оболочка».',
    seoText: [
      'ZORBAX Eclipse Plus C18 — универсальная колонка на силикагеле высокой чистоты, её часто указывают в фармакопейных и валидированных методиках. Poroshell 120 EC-C18 использует частицы 2,7 мкм с непористым ядром: эффективность близка к колонкам с частицами менее 2 мкм, а давление ниже, поэтому колонку можно ставить и на обычный ВЭЖХ.',
      'При переносе методики на Poroshell пересчитайте поток и градиент под новую геометрию колонки и проверьте пригодность системы.',
    ],
    delivery: DELIVERY_GENERAL,
    faq: [
      {
        q: 'Подойдёт ли Poroshell 120 для обычного ВЭЖХ, не УВЭЖХ?',
        a: 'Да, колонки с частицами 2,7 мкм работают при давлении, допустимом для большинства систем ВЭЖХ. Уточните предельное давление вашего прибора — подберём длину колонки.',
      },
    ],
    documents: DOCS,
    related: [
      { label: 'Продукция Agilent', href: '/brands/agilent/' },
      { label: 'Предколонки', href: '/catalog/chromatography/precolumns/' },
      { label: 'Как выбрать колонку для ВЭЖХ', href: '/articles/how-to-choose-hplc-column/' },
    ],
    facets: [...COLUMN_FACETS],
    updatedAt: '2026-10-22',
  },
  {
    parent: HPLC,
    slug: 'c18-4-6x150',
    name: 'C18 4,6 × 150 мм',
    preset: { phase: ['C18'], diameter: ['4.6'], length: ['150'] },
    h1: 'Колонки C18 4,6 × 150 мм',
    title: 'Колонки C18 4,6 × 150 мм для ВЭЖХ — Waters, Agilent, Shimadzu | ОГК-ХИМ',
    description:
      'Колонки ВЭЖХ C18 с внутренним диаметром 4,6 мм и длиной 150 мм от Waters, Agilent, Shimadzu и Welch. Сравнение по размеру частиц и pH, запрос КП.',
    intro: 'Классический формат аналитической колонки для фармацевтического анализа. Сравните колонки разных производителей по размеру частиц и рабочему диапазону pH.',
    seoText: [
      'Колонка 4,6 × 150 мм — один из самых частых форматов в фармакопейных методиках и методиках производителей лекарственных средств. Она работает на любом аналитическом ВЭЖХ при потоке около 1 мл/мин.',
      'Размер частиц определяет эффективность и давление: 5 мкм — стандарт для старых методик, 3–3,5 мкм дают более узкие пики при большем давлении. Если методика требует конкретную марку колонки, укажите её в запросе.',
    ],
    delivery: DELIVERY_GENERAL,
    documents: DOCS,
    related: [
      { label: 'Колонки Waters C18', href: '/catalog/chromatography/hplc-columns/waters-c18/' },
      { label: 'Колонки Agilent C18', href: '/catalog/chromatography/hplc-columns/agilent-c18/' },
      { label: 'Предколонки', href: '/catalog/chromatography/precolumns/' },
      { label: 'Как выбрать колонку для ВЭЖХ', href: '/articles/how-to-choose-hplc-column/' },
    ],
    facets: [...COLUMN_FACETS],
    updatedAt: '2026-10-22',
  },
  {
    parent: HPLC,
    slug: 'phenyl',
    name: 'Фенильные',
    preset: { phase: ['Phenyl'] },
    h1: 'Фенильные колонки для ВЭЖХ',
    title: 'Фенильные колонки для ВЭЖХ (Phenyl) — Agilent, Shimadzu | ОГК-ХИМ',
    description:
      'Колонки ВЭЖХ с фенильной фазой: альтернативная селективность для ароматических соединений. ZORBAX Eclipse XDB-Phenyl, Shim-pack GIST Phenyl. Запрос КП.',
    intro: 'Колонки с фенильной фазой дают другую селективность, чем C18, — пригодятся, когда на C18 не разделяются близкие по структуре ароматические соединения.',
    seoText: [
      'Фенильная фаза удерживает вещества не только за счёт гидрофобных взаимодействий, но и за счёт π–π-взаимодействий с ароматическими кольцами. Поэтому порядок выхода пиков на ней может отличаться от C18, а это помогает разделить изомеры и родственные примеси.',
      'Фенильные колонки часто используют как вторую, ортогональную колонку при разработке методики и при подтверждении чистоты пиков.',
    ],
    delivery: DELIVERY_GENERAL,
    documents: DOCS,
    related: [
      { label: 'Все колонки для ВЭЖХ', href: '/catalog/chromatography/hplc-columns/' },
      { label: 'Колонки HILIC', href: '/catalog/chromatography/hplc-columns/hilic/' },
      { label: 'Как выбрать колонку для ВЭЖХ', href: '/articles/how-to-choose-hplc-column/' },
    ],
    facets: [...COLUMN_FACETS],
    updatedAt: '2026-10-22',
  },
  {
    parent: HPLC,
    slug: 'hilic',
    name: 'HILIC',
    preset: { phase: ['HILIC'] },
    h1: 'Колонки HILIC для ВЭЖХ',
    title: 'Колонки HILIC для хроматографии полярных соединений | ОГК-ХИМ',
    description:
      'Колонки для гидрофильной хроматографии (HILIC) — удерживание полярных соединений, которые плохо удерживаются на C18. Подбор и поставка под заказ.',
    intro: 'Колонки для гидрофильной хроматографии (HILIC) удерживают полярные вещества, которые на обращённой фазе выходят с фронтом растворителя.',
    seoText: [
      'В режиме HILIC используют полярную неподвижную фазу и подвижную фазу с высоким содержанием ацетонитрила. Полярные соединения — аминокислоты, сахара, полярные метаболиты и противоионы — удерживаются тем сильнее, чем выше их полярность.',
      'Подвижная фаза с большой долей органического растворителя хорошо подходит для масс-спектрометрического детектирования. Перед первым использованием колонку HILIC уравновешивают дольше, чем обращённо-фазовую.',
    ],
    delivery: DELIVERY_GENERAL,
    documents: DOCS,
    related: [
      { label: 'Все колонки для ВЭЖХ', href: '/catalog/chromatography/hplc-columns/' },
      { label: 'Растворители для ВЭЖХ', href: '/catalog/reagents/' },
      { label: 'Как выбрать колонку для ВЭЖХ', href: '/articles/how-to-choose-hplc-column/' },
    ],
    facets: [...COLUMN_FACETS],
    updatedAt: '2026-10-22',
  },
  {
    parent: 'reference-standards/impurity-standards',
    slug: 'labeled-compounds',
    name: 'Изотопно-меченые',
    preset: { type: ['labeled'] },
    h1: 'Изотопно-меченые стандартные образцы',
    title: 'Изотопно-меченые стандарты (дейтерированные) для ЖХ-МС | ОГК-ХИМ',
    description:
      'Дейтерированные и другие изотопно-меченые соединения — внутренние стандарты для количественного анализа методом ЖХ-МС/МС. Любая фасовка под запрос.',
    intro: 'Изотопно-меченые соединения — внутренние стандарты для количественного ЖХ-МС/МС анализа в биоаналитике и при контроле примесей.',
    seoText: [
      'Изотопно-меченый внутренний стандарт химически почти не отличается от определяемого вещества, но отличается массой. Поэтому он проходит пробоподготовку и хроматографию так же, как аналит, и компенсирует потери и матричные эффекты при масс-спектрометрическом детектировании.',
      'Синтезаторы, с которыми работает ОГК-ХИМ, выпускают меченые соединения в любой фасовке под запрос: укажите количество и единицу в корзине.',
    ],
    delivery: DELIVERY_STANDARDS,
    documents: DOCS,
    related: [
      { label: 'Стандарты примесей', href: '/catalog/reference-standards/impurity-standards/' },
      { label: 'Субстанции A–Я', href: '/substances/' },
      { label: 'Холодовая цепь', href: '/services/cold-chain/' },
    ],
    facets: ['brand', 'pack', 'storage'],
    updatedAt: '2026-10-22',
  },
];

export const landingHref = (l: Pick<SeoLanding, 'parent' | 'slug'>) => `/catalog/${l.parent}/${l.slug}/`;

export function findLanding(path: string[]): SeoLanding | undefined {
  if (path.length < 2) return undefined;
  const parent = path.slice(0, -1).join('/');
  const slug = path[path.length - 1];
  return landings.find((l) => l.parent === parent && l.slug === slug);
}

const DELIVERY_STANDARDS_EN = [
  'Supplied to order from manufacturer catalogues — lead time is stated in the quotation',
  'Storage conditions are kept in transit: +2…+8 °C, −20 °C, dry ice',
  'Accompanying documents: batch certificate of analysis (CoA), safety data sheet (SDS)',
  'Delivery to any region of Russia; documents for public procurement under 44-FZ and 223-FZ',
];

const DELIVERY_GENERAL_EN = [
  'Supplied to order from manufacturer catalogues — lead time is stated in the quotation',
  'Delivery to any region of Russia',
  'Documents for public procurement under 44-FZ and 223-FZ',
];

const DOCS_EN = [
  { title: 'Company details (in Russian)', href: '/files/kartochka.pdf' },
  { title: 'Privacy policy (in Russian)', href: '/files/politika.pdf' },
];

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
    delivery: DELIVERY_GENERAL_EN,
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
    documents: DOCS_EN,
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
    delivery: DELIVERY_GENERAL_EN,
    faq: [
      {
        q: 'Is Poroshell 120 suitable for standard HPLC, not UHPLC?',
        a: 'Yes, 2.7 µm columns operate at pressures acceptable for most HPLC systems. Tell us the pressure limit of your instrument and we will select the column length.',
      },
    ],
    documents: DOCS_EN,
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
    delivery: DELIVERY_GENERAL_EN,
    documents: DOCS_EN,
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
    delivery: DELIVERY_GENERAL_EN,
    documents: DOCS_EN,
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
    delivery: DELIVERY_GENERAL_EN,
    documents: DOCS_EN,
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
    delivery: DELIVERY_STANDARDS_EN,
    documents: DOCS_EN,
    related: [
      { label: 'Impurity standards', href: '/catalog/reference-standards/impurity-standards/' },
      { label: 'Substances A–Z', href: '/substances/' },
      { label: 'Cold chain', href: '/services/cold-chain/' },
    ],
  },
};
