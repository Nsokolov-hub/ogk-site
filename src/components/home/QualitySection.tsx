import type { HomeContent } from '@/types/content';
import { Container } from '@/components/ui/Container';

/**
 * «Лучшее качество»: что ОГК-ХИМ берёт на себя — закупка, документы, доставка.
 * Пункты идут в порядке реального процесса, поэтому это <ol>; порядок виден по положению, без номеров.
 */
export function QualitySection({ quality }: { quality: HomeContent['quality'] }) {
  return (
    <section aria-labelledby="quality-title" className="mt-24 md:mt-32 lg:mt-40">
      <Container className="grid gap-10 lg:grid-cols-[minmax(0,5fr)_minmax(0,7fr)] lg:gap-16 2xl:gap-24">
        <div>
          <h2 id="quality-title" className="text-h2 font-medium text-text">
            {quality.title} <span className="text-accent">{quality.accent}</span>
          </h2>
          <p className="mt-4 max-w-[440px] text-lead text-text-secondary">{quality.subtitle}</p>
        </div>
        <ol className="grid gap-8 md:gap-10">
          {quality.items.map((item) => (
            <li key={item.id} className="grid gap-2 md:grid-cols-[200px_minmax(0,1fr)] md:gap-8 xl:grid-cols-[240px_minmax(0,1fr)]">
              <h3 className="text-h3 font-medium text-text">{item.title}</h3>
              <p className="max-w-[560px] text-lead text-text">{item.text}</p>
            </li>
          ))}
        </ol>
      </Container>
    </section>
  );
}
