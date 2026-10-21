import { ArrowDownRight } from 'lucide-react';
import { getTranslations } from 'next-intl/server';
import type { HomeContent } from '@/types/content';
import type { SiteSettings } from '@/types/settings';
import { RequestForm } from '@/components/forms/RequestForm';
import { Container } from '@/components/ui/Container';
import { Icon } from '@/components/ui/Icon';
import { SectionHeading } from '@/components/ui/SectionHeading';
import { Link } from '@/i18n/navigation';

/** «Отправьте ваш запрос»: четыре обещания лендинга + форма */
export async function RequestSection({ request, docs }: { request: HomeContent['request']; docs: SiteSettings['docs'] }) {
  const t = await getTranslations('home.request');
  return (
    <section id="request" aria-labelledby="request-title" className="mt-20 md:mt-30 lg:mt-40">
      <Container>
        <SectionHeading id="request-title" title={request.title} accent={request.accent} />
        <div className="grid gap-12 lg:grid-cols-[minmax(0,5fr)_minmax(0,7fr)] lg:gap-16 2xl:gap-24">
          <div className="order-2 lg:order-1">
            <ul className="flex flex-col gap-6 md:gap-8">
              {request.promises.map((p) => (
                <li key={p.id} className="flex items-center gap-4 md:gap-5">
                  <span className="grid size-12 shrink-0 place-items-center rounded-full bg-surface md:size-14">
                    <Icon name={p.icon} size={24} />
                  </span>
                  <span>
                    <span className="block text-body font-medium text-accent md:text-lg">{p.title}</span>
                    <span className="block text-small text-text-secondary md:text-body">{p.text}</span>
                  </span>
                </li>
              ))}
            </ul>
            <Link
              href="/contacts/"
              className="mt-10 inline-flex items-center gap-2 text-body font-medium text-text transition-colors hover:text-accent md:mt-14"
            >
              {t('toContacts')}
              <ArrowDownRight aria-hidden size={20} strokeWidth={1.5} className="text-accent" />
            </Link>
          </div>
          <div className="order-1 lg:order-2">
            <RequestForm docs={docs} />
          </div>
        </div>
      </Container>
    </section>
  );
}
