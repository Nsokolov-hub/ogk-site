import type { HomeContent } from '@/types/content';
import { Container } from '@/components/ui/Container';
import { LogoSecondary } from '@/components/ui/LogoSecondary';

/** «Почему выбирают нас» (ТЗ 11.2): абзац о компании и вторичный логотип слева, четыре преимущества справа */
export function WhyUsSection({ whyUs }: { whyUs: HomeContent['whyUs'] }) {
  return (
    <section aria-labelledby="why-title" className="mt-24 md:mt-32 lg:mt-40">
      <Container className="grid gap-12 lg:grid-cols-[minmax(0,5fr)_minmax(0,7fr)] lg:gap-16 2xl:gap-24">
        <div>
          <h2 id="why-title" className="text-h2 font-medium text-text">
            {whyUs.title} <span className="text-accent">{whyUs.accent}</span>
          </h2>
          <p className="mt-6 max-w-[560px] text-lead text-text md:mt-8">
            <span className="text-accent">{whyUs.textAccent}</span> {whyUs.text}
          </p>
          <LogoSecondary className="mt-10 h-8 md:mt-14" />
        </div>
        <ul className="grid gap-10 md:grid-cols-2 md:gap-x-12 md:gap-y-14 lg:pt-3">
          {whyUs.items.map((item) => (
            <li key={item.id}>
              <h3 className="text-h3 font-medium text-text">{item.title}</h3>
              <p className="mt-3 text-body text-text md:mt-4">{item.text}</p>
            </li>
          ))}
        </ul>
      </Container>
    </section>
  );
}
