import type { Category } from '@/types/catalog';

const rs = '/catalog/reference-standards';
const ch = '/catalog/chromatography';

/** Дерево каталога (ТЗ 4.2) */
export const catalogTree: Category[] = [
  {
    slug: 'reference-standards',
    name: 'Стандартные образцы',
    href: `${rs}/`,
    children: [
      { slug: 'edqm', name: 'EDQM', href: `${rs}/edqm/` },
      { slug: 'usp', name: 'USP', href: `${rs}/usp/` },
      { slug: 'british-pharmacopoeia', name: 'British Pharmacopoeia', href: `${rs}/british-pharmacopoeia/` },
      { slug: 'lgc', name: 'LGC', href: `${rs}/lgc/` },
      { slug: 'merck', name: 'Merck', href: `${rs}/merck/` },
      { slug: 'impurity-standards', name: 'Стандарты примесей', href: `${rs}/impurity-standards/` },
    ],
  },
  { slug: 'reagents', name: 'Реактивы', href: '/catalog/reagents/' },
  {
    slug: 'chromatography',
    name: 'Расходные материалы для хроматографии',
    href: `${ch}/`,
    children: [
      { slug: 'hplc-columns', name: 'Колонки для ВЭЖХ', href: `${ch}/hplc-columns/` },
      { slug: 'filters', name: 'Фильтры', href: `${ch}/filters/` },
      { slug: 'precolumns', name: 'Предколонки', href: `${ch}/precolumns/` },
      { slug: 'fittings', name: 'Фитинги', href: `${ch}/fittings/` },
    ],
  },
  { slug: 'reference-drugs', name: 'Референтные лекарственные препараты', href: '/catalog/reference-drugs/' },
  {
    slug: 'biological-standards',
    name: 'Микроорганизмы и биологические стандарты',
    href: '/catalog/biological-standards/',
  },
  { slug: 'laboratory-equipment', name: 'Лабораторное оборудование', href: '/catalog/laboratory-equipment/' },
  { slug: 'laboratory-glassware', name: 'Лабораторная посуда и тара', href: '/catalog/laboratory-glassware/' },
  { slug: 'pharmacopeias', name: 'Фармакопеи и справочники', href: '/catalog/pharmacopeias/' },
];

/** Короткие названия для ряда кнопок на главной */
export const categoryShortNames: Record<string, string> = {
  'reference-standards': 'Стандартные образцы',
  reagents: 'Реактивы',
  chromatography: 'Хроматография',
  'reference-drugs': 'Референтные препараты',
  'biological-standards': 'Биологические стандарты',
  'laboratory-equipment': 'Оборудование',
  'laboratory-glassware': 'Посуда и тара',
  pharmacopeias: 'Фармакопеи',
};
