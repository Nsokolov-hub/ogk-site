import { getTranslations } from 'next-intl/server';
import type { HomeContent } from '@/types/content';
import { Button } from '@/components/ui/Button';
import { Container } from '@/components/ui/Container';
import { SectionHeading } from '@/components/ui/SectionHeading';
import { ServicesAccordion } from './ServicesAccordion';

/** «Сервис под ключ»: поставка препаратов для исследований, логистика и холодовая цепь, таможня */
export async function ServicesSection({ services }: { services: HomeContent['services'] }) {
  const t = await getTranslations('home.services');
  return (
    <section aria-labelledby="services-title" className="mt-24 md:mt-32 lg:mt-40">
      <Container>
        <SectionHeading
          id="services-title"
          title={services.title}
          accent={services.accent}
          subtitle={services.subtitle}
        />
        <ServicesAccordion items={services.items} />
        <div className="mt-8 flex justify-center">
          <Button href="/services/" variant="secondary" size="m">
            {t('all')}
          </Button>
        </div>
      </Container>
    </section>
  );
}
