import type { SeoLanding } from '@/types/content';
import { DELIVERY_GENERAL, DELIVERY_STANDARDS, DOCS, RELATED_SERVICES } from './category-content';

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
