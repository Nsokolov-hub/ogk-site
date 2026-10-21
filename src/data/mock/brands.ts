import type { BrandRef } from '@/types/catalog';

const logo = (slug: string) => `/images/brands/${slug}.svg`;

/** Порядок как на текущем лендинге */
export const homeBrands: BrandRef[] = [
  { slug: 'edqm', name: 'EDQM', logo: logo('edqm') },
  { slug: 'usp', name: 'USP', logo: logo('usp') },
  { slug: 'merck', name: 'Merck', logo: logo('merck') },
  { slug: 'lgc', name: 'LGC', logo: logo('lgc') },
  { slug: 'bioorganics', name: 'BioOrganics', logo: logo('bioorganics') },
  { slug: 'synzeal', name: 'SynZeal', logo: logo('synzeal') },
  { slug: 'sciex', name: 'SCIEX', logo: logo('sciex') },
  { slug: 'waters', name: 'Waters', logo: logo('waters') },
  { slug: 'macklin', name: 'Macklin', logo: logo('macklin') },
  { slug: 'clearsynth', name: 'Clearsynth', logo: logo('clearsynth') },
  { slug: 'aozeal', name: 'Aozeal', logo: logo('aozeal') },
  { slug: 'agilent', name: 'Agilent', logo: logo('agilent') },
  { slug: 'welch', name: 'Welch', logo: logo('welch') },
];
