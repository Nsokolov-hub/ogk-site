import type { HomeContent } from '@/types/content';
import { Container } from '@/components/ui/Container';
import { Icon } from '@/components/ui/Icon';
import { SectionHeading } from '@/components/ui/SectionHeading';

/** «Лучшее качество»: три карточки с лендинга */
export function QualitySection({ quality }: { quality: HomeContent['quality'] }) {
  return (
    <section aria-labelledby="quality-title" className="mt-20 md:mt-30 lg:mt-40">
      <Container>
        <SectionHeading id="quality-title" title={quality.title} accent={quality.accent} subtitle={quality.subtitle} />
        <ul className="grid gap-3 md:gap-6 lg:grid-cols-3 2xl:gap-[34px]">
          {quality.items.map((item) => (
            <li key={item.id} className="glow flex flex-col gap-6 rounded-block bg-surface p-6 md:gap-10 md:p-[34px]">
              <div className="flex items-start justify-between gap-4">
                <h3 className="text-h3 font-medium text-text">{item.title}</h3>
                <Icon name={item.icon} size={32} />
              </div>
              <p className="text-body text-text-secondary md:text-lg">{item.text}</p>
            </li>
          ))}
        </ul>
      </Container>
    </section>
  );
}
