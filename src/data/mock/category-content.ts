import type { FacetKey } from '@/types/catalog';
import type { CategoryContent } from '@/types/content';

/**
 * Контент категорий. H1 и Title — стартовые из ТЗ 10.3, Description и тексты — черновики:
 * их пишет контент-поток по собранной семантике, факты проверяет химик (ТЗ 10.4).
 * Ключ — путь категории без /catalog/: '' — корень, 'reference-standards/edqm' — подкатегория.
 */

const STANDARD_FACETS: FacetKey[] = ['brand', 'availability', 'pack', 'storage', 'purpose', 'type'];
const COLUMN_FACETS: FacetKey[] = ['brand', 'availability', 'phase', 'length', 'diameter', 'particle', 'ph'];
const BASIC_FACETS: FacetKey[] = ['brand', 'availability'];

const DELIVERY_STANDARDS = [
  'Поставка под заказ из каталогов производителей — срок указываем в коммерческом предложении',
  'Соблюдаем условия хранения при перевозке: +2…+8 °C, −20 °C, сухой лёд',
  'Сопроводительные документы: сертификат анализа (CoA) партии, паспорт безопасности (SDS)',
  'Доставка в любой регион России, документы для закупок по 44-ФЗ и 223-ФЗ',
];

const DELIVERY_GENERAL = [
  'Поставка со склада или под заказ — срок указываем в коммерческом предложении',
  'Доставка в любой регион России',
  'Документы для закупок по 44-ФЗ и 223-ФЗ',
];

const FAQ_COMMON = [
  {
    q: 'Почему на сайте нет цен?',
    a: 'Цена зависит от фасовки, количества, условий доставки и курса. Добавьте позиции в корзину запроса — менеджер рассчитает поставку и пришлёт коммерческое предложение в течение 2 рабочих часов.',
  },
  {
    q: 'Можно заказать позицию, которой нет на сайте?',
    a: 'Да. Отправьте запрос с каталожным номером или CAS — поставим под заказ из каталогов производителей.',
  },
  {
    q: 'Можно ли получить сертификат анализа конкретной партии?',
    a: 'Да, CoA партии предоставляем по запросу — укажите это в комментарии к заявке.',
  },
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

export const categoryContent: Record<string, CategoryContent> = {
  '': {
    h1: 'Каталог',
    title: 'Каталог: стандартные образцы, реактивы и оборудование для лабораторий | ОГК-ХИМ',
    description:
      'Стандартные образцы, реактивы, расходные материалы для хроматографии, оборудование и фармакопеи для фармацевтических лабораторий. Поиск по кат. № и CAS, запрос КП.',
    intro: 'Стандартные образцы, реактивы, хроматография и оборудование ведущих производителей. Ищите по каталожному номеру или CAS — или добавляйте позиции в корзину запроса.',
    facets: BASIC_FACETS,
    delivery: DELIVERY_GENERAL,
    faq: FAQ_COMMON,
    documents: DOCS,
    related: [
      { label: 'Стандартные образцы EDQM', href: '/catalog/reference-standards/edqm/' },
      { label: 'Колонки для ВЭЖХ', href: '/catalog/chromatography/hplc-columns/' },
      ...RELATED_SERVICES,
    ],
  },

  'reference-standards': {
    h1: 'Стандартные образцы для лабораторий',
    title: 'Стандартные образцы для лабораторий — поставка | ОГК-ХИМ',
    description:
      'Фармакопейные и вторичные стандартные образцы EDQM, USP, BP, LGC, Merck и стандарты примесей. Поставка под заказ с документами и соблюдением условий хранения.',
    intro:
      'Фармакопейные стандартные образцы EDQM, USP и British Pharmacopoeia, вторичные стандарты и стандарты примесей. Поставляем под заказ с соблюдением условий хранения.',
    facets: STANDARD_FACETS,
    seoText: [
      'Стандартные образцы нужны для идентификации, количественного определения и контроля примесей в лекарственных средствах. Фармакопейные стандарты EDQM, USP и British Pharmacopoeia применяются в испытаниях по соответствующим фармакопейным статьям.',
      'Вторичные стандарты (например, Pharmaceutical Secondary Standards) прослеживаются к первичным фармакопейным образцам и подходят для рутинного контроля. Стандарты примесей и меченые соединения синтезаторы поставляют в любой фасовке под запрос.',
    ],
    delivery: DELIVERY_STANDARDS,
    faq: [
      ...FAQ_COMMON,
      {
        q: 'Чем стандарты EDQM отличаются от USP?',
        a: 'EDQM выпускает стандартные образцы Европейской фармакопеи, USP — Фармакопеи США. Выбор зависит от того, по какой фармакопейной статье выполняется испытание.',
      },
    ],
    documents: DOCS,
    related: [
      { label: 'Стандарты примесей', href: '/catalog/reference-standards/impurity-standards/' },
      { label: 'Колонки для ВЭЖХ', href: '/catalog/chromatography/hplc-columns/' },
      { label: 'Реактивы', href: '/catalog/reagents/' },
      ...RELATED_SERVICES,
    ],
  },
  'reference-standards/edqm': {
    h1: 'Стандартные образцы EDQM',
    title: 'Стандартные образцы EDQM — поставка в Россию | ОГК-ХИМ',
    description: 'Стандартные образцы Европейской фармакопеи (EDQM CRS): поставка под заказ в Россию, документы, соблюдение условий хранения. Запрос КП.',
    intro: 'Стандартные образцы Европейской фармакопеи (CRS). Поставляются в фиксированной фасовке производителя.',
    facets: STANDARD_FACETS,
    delivery: DELIVERY_STANDARDS,
    faq: FAQ_COMMON,
    documents: DOCS,
    related: [
      { label: 'Стандартные образцы USP', href: '/catalog/reference-standards/usp/' },
      { label: 'Стандарты примесей', href: '/catalog/reference-standards/impurity-standards/' },
      ...RELATED_SERVICES,
    ],
  },
  'reference-standards/usp': {
    h1: 'Стандартные образцы USP',
    title: 'Стандартные образцы USP — поставка для лабораторий | ОГК-ХИМ',
    description: 'Стандартные образцы Фармакопеи США (USP RS): поставка под заказ, документы, соблюдение условий хранения. Запрос КП.',
    intro: 'Стандартные образцы Фармакопеи США (Reference Standards) в фиксированной фасовке производителя.',
    facets: STANDARD_FACETS,
    delivery: DELIVERY_STANDARDS,
    faq: FAQ_COMMON,
    documents: DOCS,
    related: [
      { label: 'Стандартные образцы EDQM', href: '/catalog/reference-standards/edqm/' },
      { label: 'Стандарты примесей', href: '/catalog/reference-standards/impurity-standards/' },
      ...RELATED_SERVICES,
    ],
  },
  'reference-standards/british-pharmacopoeia': {
    h1: 'Стандартные образцы British Pharmacopoeia',
    title: 'Стандартные образцы British Pharmacopoeia — ОГК-ХИМ',
    description: 'Стандартные образцы Британской фармакопеи (BPCRS): поставка под заказ, документы. Запрос КП.',
    intro: 'Химические стандартные образцы Британской фармакопеи (BPCRS).',
    facets: STANDARD_FACETS,
    delivery: DELIVERY_STANDARDS,
    faq: FAQ_COMMON,
    documents: DOCS,
    related: [{ label: 'Фармакопеи и справочники', href: '/catalog/pharmacopeias/' }, ...RELATED_SERVICES],
  },
  'reference-standards/lgc': {
    h1: 'Стандартные образцы LGC',
    title: 'Стандартные образцы LGC — поставка | ОГК-ХИМ',
    description: 'Стандартные образцы LGC: поставка под заказ в нескольких фасовках, документы. Запрос КП.',
    intro: 'Стандартные образцы LGC в нескольких фасовках на выбор.',
    facets: STANDARD_FACETS,
    delivery: DELIVERY_STANDARDS,
    faq: FAQ_COMMON,
    documents: DOCS,
    related: RELATED_SERVICES,
  },
  'reference-standards/merck': {
    h1: 'Стандартные образцы Merck',
    title: 'Вторичные стандартные образцы Merck — поставка | ОГК-ХИМ',
    description: 'Вторичные фармацевтические стандарты Merck (Pharmaceutical Secondary Standards): поставка под заказ, документы. Запрос КП.',
    intro: 'Вторичные фармацевтические стандарты (Pharmaceutical Secondary Standards; Certified Reference Materials).',
    facets: STANDARD_FACETS,
    delivery: DELIVERY_STANDARDS,
    faq: FAQ_COMMON,
    documents: DOCS,
    related: [{ label: 'Продукция Merck', href: '/brands/merck/' }, ...RELATED_SERVICES],
  },
  'reference-standards/impurity-standards': {
    h1: 'Стандарты примесей',
    title: 'Стандарты примесей SynZeal, Clearsynth, TRC и других — ОГК-ХИМ',
    description: 'Стандарты фармакопейных примесей, метаболитов и меченых соединений. Любая фасовка под запрос. Поставка под заказ, запрос КП.',
    intro: 'Примеси, метаболиты и меченые соединения от синтезаторов. Любая фасовка под запрос — укажите нужное количество в корзине.',
    facets: STANDARD_FACETS,
    delivery: DELIVERY_STANDARDS,
    faq: [
      ...FAQ_COMMON,
      {
        q: 'Можно заказать нестандартную фасовку?',
        a: 'Да. У стандартов примесей выберите «Своя фасовка» и укажите количество в мг, г или мл.',
      },
    ],
    documents: DOCS,
    related: RELATED_SERVICES,
  },

  reagents: {
    h1: 'Реактивы для фармацевтических лабораторий',
    title: 'Лабораторные реактивы для фармацевтики — поставка | ОГК-ХИМ',
    description: 'Растворители для ВЭЖХ и ЖХ-МС, кислоты, соли и индикаторы для фармацевтических лабораторий. Поставка со склада и под заказ, запрос КП.',
    intro: 'Растворители для ВЭЖХ и ЖХ-МС, кислоты, соли, буферные компоненты и индикаторы.',
    facets: ['brand', 'availability', 'pack', 'storage'],
    delivery: DELIVERY_GENERAL,
    faq: FAQ_COMMON,
    documents: DOCS,
    related: [{ label: 'Колонки для ВЭЖХ', href: '/catalog/chromatography/hplc-columns/' }, ...RELATED_SERVICES],
  },

  chromatography: {
    h1: 'Расходные материалы для хроматографии',
    title: 'Расходные материалы для хроматографии — ОГК-ХИМ',
    description: 'Колонки и предколонки для ВЭЖХ, фильтры, фитинги Waters, Agilent, Shimadzu, Welch. Подбор под методику, запрос КП.',
    intro: 'Колонки и предколонки для ВЭЖХ и УВЭЖХ, шприцевые фильтры и фитинги. Поможем подобрать колонку под методику.',
    facets: COLUMN_FACETS,
    delivery: DELIVERY_GENERAL,
    faq: FAQ_COMMON,
    documents: DOCS,
    related: [{ label: 'Растворители для ВЭЖХ', href: '/catalog/reagents/' }, ...RELATED_SERVICES],
  },
  'chromatography/hplc-columns': {
    h1: 'Колонки для ВЭЖХ',
    title: 'Колонки для ВЭЖХ — Waters, Agilent, Shimadzu и другие | ОГК-ХИМ',
    description: 'Колонки для ВЭЖХ и УВЭЖХ: C18, C8, Phenyl, HILIC. Фильтры по длине, диаметру, размеру частиц и pH. Запрос КП.',
    intro: 'Колонки для ВЭЖХ и УВЭЖХ. Подберите по фазе, длине, внутреннему диаметру, размеру частиц и рабочему диапазону pH.',
    facets: COLUMN_FACETS,
    delivery: DELIVERY_GENERAL,
    faq: [
      ...FAQ_COMMON,
      {
        q: 'Поможете подобрать колонку под методику?',
        a: 'Да. Опишите методику или пришлите фармакопейную статью — специалист предложит колонку и совместимую предколонку.',
      },
    ],
    documents: DOCS,
    related: [
      { label: 'Предколонки', href: '/catalog/chromatography/precolumns/' },
      { label: 'Фильтры', href: '/catalog/chromatography/filters/' },
      ...RELATED_SERVICES,
    ],
  },
  'chromatography/filters': {
    h1: 'Фильтры для хроматографии',
    title: 'Фильтры для ВЭЖХ и хроматографии — ОГК-ХИМ',
    description: 'Шприцевые фильтры PTFE, Nylon, PVDF, PES и RC для пробоподготовки к ВЭЖХ. Запрос КП.',
    intro: 'Шприцевые фильтры для пробоподготовки: мембраны PTFE, Nylon, PVDF, PES и RC.',
    facets: BASIC_FACETS,
    delivery: DELIVERY_GENERAL,
    faq: FAQ_COMMON,
    documents: DOCS,
    related: [{ label: 'Колонки для ВЭЖХ', href: '/catalog/chromatography/hplc-columns/' }],
  },
  'chromatography/precolumns': {
    h1: 'Предколонки для ВЭЖХ',
    title: 'Предколонки для ВЭЖХ и хроматографии — ОГК-ХИМ',
    description: 'Предколонки и защитные картриджи для колонок ВЭЖХ и УВЭЖХ. Запрос КП.',
    intro: 'Предколонки и защитные картриджи продлевают срок службы аналитической колонки.',
    facets: ['brand', 'availability', 'phase', 'ph'],
    delivery: DELIVERY_GENERAL,
    faq: FAQ_COMMON,
    documents: DOCS,
    related: [{ label: 'Колонки для ВЭЖХ', href: '/catalog/chromatography/hplc-columns/' }],
  },
  'chromatography/fittings': {
    h1: 'Фитинги для хроматографии',
    title: 'Фитинги и капилляры для ВЭЖХ — ОГК-ХИМ',
    description: 'Фитинги, обжимные кольца, соединители и капилляры для систем ВЭЖХ. Запрос КП.',
    intro: 'Фитинги, обжимные кольца, соединители и капилляры для систем ВЭЖХ.',
    facets: BASIC_FACETS,
    delivery: DELIVERY_GENERAL,
    faq: FAQ_COMMON,
    documents: DOCS,
    related: [{ label: 'Колонки для ВЭЖХ', href: '/catalog/chromatography/hplc-columns/' }],
  },

  'reference-drugs': {
    h1: 'Референтные лекарственные препараты',
    title: 'Референтные лекарственные препараты для исследований | ОГК-ХИМ',
    description: 'Поставка референтных лекарственных препаратов в Россию для исследовательских целей. Запрос КП.',
    intro: 'Референтные лекарственные препараты для сравнительных исследований — поставка в Россию для исследовательских целей.',
    facets: ['brand', 'availability'],
    delivery: DELIVERY_GENERAL,
    faq: FAQ_COMMON,
    documents: DOCS,
    related: [{ label: 'Поставка препаратов для исследований', href: '/services/research-drug-supply/' }, ...RELATED_SERVICES],
  },
  'biological-standards': {
    h1: 'Микроорганизмы и биологические стандарты',
    title: 'Микроорганизмы и биологические стандарты для лабораторий | ОГК-ХИМ',
    description: 'Тест-штаммы ATCC для микробиологического контроля. Поставка с соблюдением холодовой цепи, запрос КП.',
    intro: 'Тест-штаммы микроорганизмов ATCC для микробиологического контроля качества.',
    facets: ['brand', 'availability', 'storage'],
    delivery: DELIVERY_STANDARDS,
    faq: FAQ_COMMON,
    documents: DOCS,
    related: [{ label: 'Холодовая цепь', href: '/services/cold-chain/' }],
  },
  'laboratory-equipment': {
    h1: 'Лабораторное оборудование',
    title: 'Лабораторное оборудование для фармацевтических компаний | ОГК-ХИМ',
    description: 'Хроматографы, детекторы и спектрофотометры Shimadzu, Agilent, Waters. Поставка и ввоз в Россию, запрос КП.',
    intro: 'Хроматографические системы, модули и спектрофотометры ведущих производителей.',
    facets: BASIC_FACETS,
    delivery: DELIVERY_GENERAL,
    faq: FAQ_COMMON,
    documents: DOCS,
    related: [{ label: 'Колонки для ВЭЖХ', href: '/catalog/chromatography/hplc-columns/' }, ...RELATED_SERVICES],
  },
  'laboratory-glassware': {
    h1: 'Лабораторная посуда и тара',
    title: 'Лабораторная посуда и тара — ОГК-ХИМ',
    description: 'Виалы, крышки, мерные колбы и лабораторная посуда. Запрос КП.',
    intro: 'Виалы и крышки для автосамплеров, мерные колбы, бутыли и стаканы.',
    facets: BASIC_FACETS,
    delivery: DELIVERY_GENERAL,
    faq: FAQ_COMMON,
    documents: DOCS,
    related: [{ label: 'Фильтры для хроматографии', href: '/catalog/chromatography/filters/' }],
  },
  pharmacopeias: {
    h1: 'Фармакопеи и справочники',
    title: 'Фармакопеи и подписки на онлайн-фармакопеи — ОГК-ХИМ',
    description: 'Европейская фармакопея, USP–NF, Британская фармакопея: печатные издания и годовые онлайн-подписки. Запрос КП.',
    intro: 'Печатные издания и годовые подписки на онлайн-фармакопеи.',
    facets: BASIC_FACETS,
    delivery: DELIVERY_GENERAL,
    faq: FAQ_COMMON,
    documents: DOCS,
    related: [{ label: 'Стандартные образцы', href: '/catalog/reference-standards/' }],
  },
};
