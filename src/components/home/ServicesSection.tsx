import { ArrowRight } from 'lucide-react';
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
    <section aria-labelledby="services-title" className="mt-20 md:mt-30 lg:mt-40">
      <Container>
        <SectionHeading
          id="services-title"
          title={services.title}
          accent={services.accent}
          subtitle={services.subtitle}
          action={
            <Button href="/services/" variant="ghost" size="m" icon={<ArrowRight aria-hidden size={20} strokeWidth={1.5} />}>
              {t('all')}
            </Button>
          }
        />
        <ServicesAccordion items={services.items} />
      </Container>
    </section>
  );
}
