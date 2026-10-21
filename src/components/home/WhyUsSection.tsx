import type { HomeContent } from '@/types/content';
import { Container } from '@/components/ui/Container';
import { Icon } from '@/components/ui/Icon';
import { LogoSecondary } from '@/components/ui/LogoSecondary';

/** «Почему выбирают нас»: абзац о компании с линией и вторичным логотипом + 4 преимущества */
export function WhyUsSection({ whyUs }: { whyUs: HomeContent['whyUs'] }) {
  return (
    <section aria-labelledby="why-title" className="mt-20 md:mt-30 lg:mt-40">
      <Container className="grid gap-10 lg:grid-cols-[minmax(0,5fr)_minmax(0,7fr)] lg:gap-16 2xl:gap-24">
        <div>
          <h2 id="why-title" className="text-h2 font-medium text-text">
            {whyUs.title} <span className="text-accent">{whyUs.accent}</span>
          </h2>
          <p className="mt-6 text-body text-text md:mt-8 md:text-lg">
            <span className="text-accent">{whyUs.textAccent}</span> {whyUs.text}
          </p>
          <div aria-hidden className="mt-10 flex items-center gap-6 md:mt-16">
            <span className="h-px flex-1 bg-accent" />
            <LogoSecondary />
          </div>
        </div>
        <ul className="grid gap-8 md:grid-cols-2 md:gap-x-10 md:gap-y-12 lg:pt-4">
          {whyUs.items.map((item) => (
            <li key={item.id}>
              <h3 className="flex items-center gap-3 text-h4 font-medium text-accent">
                <Icon name={item.icon} size={26} />
                {item.title}
              </h3>
              <p className="mt-3 text-body text-text-secondary md:mt-4">{item.text}</p>
            </li>
          ))}
        </ul>
      </Container>
    </section>
  );
}
