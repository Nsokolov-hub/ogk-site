import type { SolutionContent } from '@/types/content';

/**
 * Отраслевые решения (ТЗ 4.1, 4.2): pharmaceutical-quality-control, hplc-laboratory, pharmaceutical-rnd,
 * microbiology-laboratory. Тексты — черновики контент-потока, факты проверяет химик (ТЗ 10.4).
 */

const RS = '/catalog/reference-standards';
const CH = '/catalog/chromatography';

export const solutions: SolutionContent[] = [
  {
    slug: 'pharmaceutical-quality-control',
    name: 'Лаборатория контроля качества',
    h1: 'Всё для лаборатории контроля качества',
    title: 'Оснащение лаборатории контроля качества: стандарты, колонки, реактивы | ОГК-ХИМ',
    description:
      'Стандартные образцы EDQM, USP и BP, стандарты примесей, колонки для ВЭЖХ, реактивы, фармакопеи и тест-штаммы для лаборатории ОКК фармацевтического предприятия. Один запрос — одно КП.',
    summary: 'Стандартные образцы, примеси, колонки, реактивы и фармакопеи для испытаний по монографиям.',
    intro:
      'Стандартные образцы, колонки, реактивы и фармакопеи для испытаний по монографиям и методикам предприятия. Соберите всё в одну корзину — пришлём одно коммерческое предложение в течение 2 рабочих часов.',
    tasks: [
      'Испытания по монографиям Ph. Eur., USP и BP',
      'Контроль примесей и валидация методик',
      'Входной контроль субстанций и выпуск серий',
      'Микробиологическая чистота и испытания на стерильность',
    ],
    groups: [
      {
        title: 'Фармакопейные стандарты',
        text: 'Первичные стандарты EDQM, USP и British Pharmacopoeia для испытаний строго по монографии, вторичные стандарты Merck — для рутинного контроля.',
        links: [
          { label: 'EDQM', href: `${RS}/edqm/` },
          { label: 'USP', href: `${RS}/usp/` },
          { label: 'British Pharmacopoeia', href: `${RS}/british-pharmacopoeia/` },
          { label: 'Вторичные Merck', href: `${RS}/merck/` },
        ],
        scope: ['reference-standards/edqm', 'reference-standards/usp', 'reference-standards/british-pharmacopoeia', 'reference-standards/merck'],
      },
      {
        title: 'Стандарты примесей',
        text: 'Примеси по Ph. Eur. и USP, метаболиты и меченые соединения от SynZeal, Clearsynth, TRC и Aozeal — в любой фасовке под запрос.',
        links: [
          { label: 'Стандарты примесей', href: `${RS}/impurity-standards/` },
          { label: 'Изотопно-меченые', href: `${RS}/impurity-standards/labeled-compounds/` },
          { label: 'Субстанции A–Я', href: '/substances/' },
        ],
        scope: ['reference-standards/impurity-standards'],
      },
      {
        title: 'Хроматография',
        text: 'Колонки и предколонки для ВЭЖХ и УВЭЖХ, шприцевые фильтры и фитинги. Подберём колонку под методику.',
        links: [
          { label: 'Колонки для ВЭЖХ', href: `${CH}/hplc-columns/` },
          { label: 'Колонки C18 4,6 × 150 мм', href: `${CH}/hplc-columns/c18-4-6x150/` },
          { label: 'Предколонки', href: `${CH}/precolumns/` },
          { label: 'Фильтры', href: `${CH}/filters/` },
        ],
        scope: ['chromatography'],
      },
      {
        title: 'Реактивы и растворители',
        text: 'Растворители для ВЭЖХ и ЖХ-МС, кислоты и соли для подвижных фаз и пробоподготовки.',
        links: [{ label: 'Реактивы', href: '/catalog/reagents/' }],
        scope: ['reagents'],
      },
      {
        title: 'Фармакопеи',
        text: 'Печатные издания и годовые онлайн-подписки на Европейскую, Британскую фармакопеи и USP–NF.',
        links: [{ label: 'Фармакопеи и справочники', href: '/catalog/pharmacopeias/' }],
        scope: ['pharmacopeias'],
      },
      {
        title: 'Тест-штаммы',
        text: 'Штаммы ATCC для испытаний на микробиологическую чистоту, стерильность и эффективность консервантов.',
        links: [{ label: 'Микроорганизмы и биологические стандарты', href: '/catalog/biological-standards/' }],
        scope: ['biological-standards'],
      },
    ],
    featured: ['reference-standards/edqm', 'reference-standards/usp', 'reference-standards/impurity-standards', 'chromatography/hplc-columns'],
    services: ['cold-chain', 'customs-clearance', 'import-permits'],
    articles: ['edqm-vs-usp', 'how-to-choose-reference-standard', 'what-are-edqm-reference-standards', 'how-to-order-standards-from-europe'],
    faq: [
      {
        q: 'Можно отправить один запрос на стандарты, колонки и реактивы?',
        a: 'Да. Добавьте позиции из разных разделов в одну корзину или загрузите список до 200 строк — пришлём одно коммерческое предложение.',
      },
      {
        q: 'Предоставляете документы для закупки по 44-ФЗ и 223-ФЗ?',
        a: 'Да. Укажите требования к документам в комментарии к заявке — подготовим комплект вместе с коммерческим предложением.',
      },
      {
        q: 'Как перевозите стандарты с хранением при −20 °C?',
        a: 'В термоконтейнерах с хладоэлементами или сухим льдом и логгером температуры. Запись логгера передаём вместе с грузом.',
      },
    ],
    updatedAt: '2026-10-22',
  },
  {
    slug: 'hplc-laboratory',
    name: 'Лаборатория ВЭЖХ',
    h1: 'Оснащение лаборатории ВЭЖХ',
    title: 'Оснащение лаборатории ВЭЖХ: колонки, предколонки, фильтры, приборы | ОГК-ХИМ',
    description:
      'Колонки и предколонки Waters, Agilent, Shimadzu и Welch, шприцевые фильтры, фитинги, растворители и приборы для ВЭЖХ. Подбор колонки под методику и одно КП на весь список.',
    summary: 'Колонки, предколонки, фильтры, фитинги, растворители и приборы для ВЭЖХ и УВЭЖХ.',
    intro:
      'Колонки, предколонки, фильтры, фитинги и растворители для ВЭЖХ и УВЭЖХ, а также модули хроматографов. Пришлите методику — подберём колонку и всё, что к ней нужно.',
    tasks: [
      'Подбор колонки под фармакопейную методику',
      'Перенос методики с ВЭЖХ на УВЭЖХ',
      'Регулярное пополнение расходников',
      'Оснащение новой хроматографической линии',
    ],
    groups: [
      {
        title: 'Колонки для ВЭЖХ и УВЭЖХ',
        text: 'C18, C8, фенильные и HILIC от Waters, Agilent, Shimadzu и Welch. Фильтры по длине, диаметру, размеру частиц и pH.',
        links: [
          { label: 'Все колонки', href: `${CH}/hplc-columns/` },
          { label: 'Waters C18', href: `${CH}/hplc-columns/waters-c18/` },
          { label: 'Agilent C18', href: `${CH}/hplc-columns/agilent-c18/` },
          { label: 'Фенильные', href: `${CH}/hplc-columns/phenyl/` },
          { label: 'HILIC', href: `${CH}/hplc-columns/hilic/` },
        ],
        scope: ['chromatography/hplc-columns'],
      },
      {
        title: 'Предколонки',
        text: 'Защитные картриджи и держатели VanGuard, Sentry, ZORBAX Guard и Fast Guard продлевают срок службы колонки.',
        links: [{ label: 'Предколонки', href: `${CH}/precolumns/` }],
        scope: ['chromatography/precolumns'],
      },
      {
        title: 'Пробоподготовка',
        text: 'Шприцевые фильтры PTFE, Nylon, PVDF, PES и RC с порами 0,22 и 0,45 мкм, виалы и крышки для автосамплера.',
        links: [
          { label: 'Фильтры', href: `${CH}/filters/` },
          { label: 'Посуда и тара', href: '/catalog/laboratory-glassware/' },
        ],
        scope: ['chromatography/filters', 'laboratory-glassware'],
      },
      {
        title: 'Фитинги и капилляры',
        text: 'PEEK-фитинги, обжимные кольца, соединители и капилляры — без мёртвого объёма.',
        links: [{ label: 'Фитинги', href: `${CH}/fittings/` }],
        scope: ['chromatography/fittings'],
      },
      {
        title: 'Растворители',
        text: 'Ацетонитрил, метанол и другие растворители квалификации для ВЭЖХ и ЖХ-МС.',
        links: [{ label: 'Реактивы', href: '/catalog/reagents/' }],
        scope: ['reagents'],
      },
      {
        title: 'Приборы и модули',
        text: 'Хроматографы, насосы и детекторы Waters, Agilent и Shimadzu, спектрофотометры.',
        links: [{ label: 'Лабораторное оборудование', href: '/catalog/laboratory-equipment/' }],
        scope: ['laboratory-equipment'],
      },
    ],
    featured: ['chromatography/hplc-columns', 'chromatography/precolumns', 'chromatography/filters'],
    services: ['customs-clearance', 'tn-ved'],
    articles: ['how-to-choose-hplc-column', 'hplc-consumables', 'why-use-guard-columns'],
    faq: [
      {
        q: 'Подберёте колонку, если в методике указана снятая с производства?',
        a: 'Да. Пришлите методику — предложим колонку с близкой фазой, геометрией и селективностью. Перед заменой в валидированной методике проверьте пригодность системы.',
      },
      {
        q: 'Можно заказать колонку вместе с совместимой предколонкой?',
        a: 'Да. Добавьте колонку в корзину и отметьте в комментарии, что нужна предколонка, — включим картридж и держатель в КП.',
      },
    ],
    updatedAt: '2026-10-22',
  },
  {
    slug: 'pharmaceutical-rnd',
    name: 'Фармацевтическая разработка',
    h1: 'Материалы для фармацевтической разработки',
    title: 'Материалы для фармразработки: референтные препараты, стандарты, примеси | ОГК-ХИМ',
    description:
      'Референтные препараты для исследований биоэквивалентности, стандарты субстанций и примесей, изотопно-меченые соединения и реактивы для R&D. Ввоз под разрешение Минздрава и холодовая цепь.',
    summary: 'Референтные препараты, стандарты API и примесей, меченые соединения и реактивы для R&D.',
    intro:
      'Референтные препараты, стандарты субстанций и примесей, меченые соединения и реактивы для разработки воспроизведённых препаратов. Организуем ввоз под разрешение и перевозку в нужном температурном режиме.',
    tasks: [
      'Разработка воспроизведённого препарата',
      'Тест сравнительной кинетики растворения',
      'Исследования биоэквивалентности',
      'Разработка и валидация аналитических методик',
    ],
    groups: [
      {
        title: 'Референтные препараты',
        text: 'Оригинальные препараты для сравнения при разработке и в исследованиях биоэквивалентности. Несколько серий с нужным остаточным сроком годности.',
        links: [
          { label: 'Референтные препараты', href: '/catalog/reference-drugs/' },
          { label: 'Поставка для исследований', href: '/services/research-drug-supply/' },
        ],
        scope: ['reference-drugs'],
      },
      {
        title: 'Стандарты субстанций',
        text: 'Фармакопейные и вторичные стандарты API для количественного определения и идентификации.',
        links: [
          { label: 'Стандартные образцы', href: `${RS}/` },
          { label: 'Субстанции A–Я', href: '/substances/' },
        ],
        scope: ['reference-standards/edqm', 'reference-standards/usp', 'reference-standards/lgc', 'reference-standards/merck'],
      },
      {
        title: 'Примеси и метаболиты',
        text: 'Стандарты примесей для изучения профиля примесей и валидации методик — любая фасовка под запрос.',
        links: [{ label: 'Стандарты примесей', href: `${RS}/impurity-standards/` }],
        scope: ['reference-standards/impurity-standards'],
      },
      {
        title: 'Меченые соединения',
        text: 'Дейтерированные внутренние стандарты для биоаналитики методом ЖХ-МС/МС.',
        links: [{ label: 'Изотопно-меченые', href: `${RS}/impurity-standards/labeled-compounds/` }],
        scope: ['reference-standards/impurity-standards'],
      },
    ],
    featured: ['reference-drugs', 'reference-standards/impurity-standards'],
    services: ['research-drug-supply', 'import-permits', 'cold-chain'],
    articles: ['what-is-reference-drug', 'how-to-choose-reference-standard', 'pharma-shipping-2-8'],
    faq: [
      {
        q: 'Поможете с разрешением на ввоз незарегистрированного препарата?',
        a: 'Да. Подготовим комплект документов для разрешения Минздрава на ввоз партии для исследований и организуем поставку после его получения.',
      },
      {
        q: 'Можно получить несколько серий референтного препарата?',
        a: 'Да. Укажите в запросе число серий и минимальный остаточный срок годности — подберём партии под график исследований.',
      },
    ],
    updatedAt: '2026-10-22',
  },
  {
    slug: 'microbiology-laboratory',
    name: 'Микробиологическая лаборатория',
    h1: 'Оснащение микробиологической лаборатории',
    title: 'Тест-штаммы ATCC и оснащение микробиологической лаборатории | ОГК-ХИМ',
    description:
      'Тест-штаммы ATCC для фармакопейных микробиологических испытаний, лабораторная посуда и фармакопеи. Перевозка штаммов в нужном температурном режиме.',
    summary: 'Тест-штаммы ATCC, посуда и фармакопеи для микробиологических испытаний.',
    intro:
      'Тест-штаммы ATCC для испытаний на микробиологическую чистоту, стерильность и эффективность консервантов, а также посуда и фармакопеи. Штаммы перевозим в нужном температурном режиме.',
    tasks: [
      'Испытание на микробиологическую чистоту',
      'Испытание на стерильность',
      'Проверка ростовых свойств питательных сред',
      'Испытание эффективности антимикробных консервантов',
    ],
    groups: [
      {
        title: 'Тест-штаммы ATCC',
        text: 'Escherichia coli, Staphylococcus aureus, Pseudomonas aeruginosa, Candida albicans, Aspergillus brasiliensis, Bacillus subtilis и другие штаммы, указанные в фармакопеях.',
        links: [{ label: 'Микроорганизмы и биологические стандарты', href: '/catalog/biological-standards/' }],
        scope: ['biological-standards'],
      },
      {
        title: 'Лабораторная посуда',
        text: 'Мерные колбы класса A, лабораторные бутыли и стаканы DURAN.',
        links: [{ label: 'Посуда и тара', href: '/catalog/laboratory-glassware/' }],
        scope: ['laboratory-glassware'],
      },
      {
        title: 'Фармакопеи',
        text: 'Европейская и Британская фармакопеи, USP–NF — печатные издания и онлайн-подписки.',
        links: [{ label: 'Фармакопеи', href: '/catalog/pharmacopeias/' }],
        scope: ['pharmacopeias'],
      },
    ],
    featured: ['biological-standards'],
    services: ['cold-chain', 'import-permits', 'customs-clearance'],
    articles: ['what-is-cold-chain', 'pharma-shipping-2-8'],
    faq: [
      {
        q: 'В каком виде поставляются штаммы ATCC?',
        a: 'Как правило, в лиофилизированном виде во флаконе. Условия хранения указаны в карточке штамма и паспорте.',
      },
      {
        q: 'Нужны ли документы на ввоз штаммов?',
        a: 'Зависит от штамма и его группы патогенности. Уточним требования по вашему списку и поможем с разрешительными документами, если они нужны.',
      },
    ],
    updatedAt: '2026-10-22',
  },
];
