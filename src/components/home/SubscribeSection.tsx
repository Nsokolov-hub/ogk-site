import type { HomeContent } from '@/types/content';
import type { SiteSettings } from '@/types/settings';
import { SubscribeForm } from '@/components/forms/SubscribeForm';
import { Container } from '@/components/ui/Container';

/** Сбор e-mail (Feedback): блок со свечением и формой подписки */
export function SubscribeSection({ subscribe, docs }: { subscribe: HomeContent['subscribe']; docs: SiteSettings['docs'] }) {
  return (
    <section aria-labelledby="subscribe-title" className="mt-20 md:mt-30 lg:mt-40">
      <Container>
        <div data-active="true" className="glow grid gap-8 rounded-block bg-surface p-6 md:p-10 lg:grid-cols-[minmax(0,5fr)_minmax(0,7fr)] lg:items-start lg:gap-16 lg:p-14 2xl:gap-24">
          <div>
            <h2 id="subscribe-title" className="text-h3 font-medium text-text">
              {subscribe.title} <span className="text-accent">{subscribe.accent}</span>
            </h2>
            <p className="mt-3 text-body text-text-secondary md:text-lg">{subscribe.text}</p>
          </div>
          <SubscribeForm docs={docs} />
        </div>
      </Container>
    </section>
  );
}
