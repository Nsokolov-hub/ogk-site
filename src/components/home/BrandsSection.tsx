import type { HomeContent } from '@/types/content';
import { Container } from '@/components/ui/Container';
import { SectionHeading } from '@/components/ui/SectionHeading';
import { BrandsRow } from './BrandsRow';
import { CatalogPromo } from './CatalogPromo';

/** «Широкий ассортимент»: логотипы ведут на страницы брендов + промо «Нужен конкретный товар?» */
export function BrandsSection({ brands, promo }: { brands: HomeContent['brands']; promo: HomeContent['promo'] }) {
  return (
    <section aria-labelledby="brands-title" className="mt-24 md:mt-32 lg:mt-40">
      <Container>
        <SectionHeading id="brands-title" title={brands.title} accent={brands.accent} subtitle={brands.subtitle} />
        <BrandsRow items={brands.items} />
        <CatalogPromo promo={promo} />
      </Container>
    </section>
  );
}
