import { getTranslations } from 'next-intl/server';
import type { HomeContent } from '@/types/content';
import type { SiteSettings } from '@/types/settings';
import { RequestForm } from '@/components/forms/RequestForm';
import { ArrowRight } from 'lucide-react';
import { Icon } from '@/components/ui/Icon';
import { Container } from '@/components/ui/Container';
import { SectionHeading } from '@/components/ui/SectionHeading';
import { Link } from '@/i18n/navigation';

/** «Отправьте ваш запрос»: четыре обещания лендинга + форма */
export async function RequestSection({ request, docs }: { request: HomeContent['request']; docs: SiteSettings['docs'] }) {
  const t = await getTranslations('home.request');
  return (
    <section id="request" aria-labelledby="request-title" className="mt-24 md:mt-32 lg:mt-40">
      <Container>
        <SectionHeading id="request-title" title={request.title} accent={request.accent} />
        <div className="grid gap-12 lg:grid-cols-[minmax(0,5fr)_minmax(0,7fr)] lg:gap-16 2xl:gap-24">
          <div className="order-2 lg:order-1">
            <ul className="flex flex-col gap-7 lg:gap-12">
              {request.promises.map((p) => (
                <li key={p.id} className="flex items-start gap-5 lg:gap-8">
                  <span className="grid size-14 shrink-0 place-items-center rounded-full bg-surface"><Icon name={p.icon} /></span>
                  <div>
                    <span className="block text-h4 font-medium text-text">{p.title}</span>
                    <span className="mt-1.5 block text-body text-text-secondary">{p.text}</span>
                  </div>
                </li>
              ))}
            </ul>
            <Link
              href="/contacts/"
              className="mt-10 inline-flex items-center gap-3 lg:ml-[88px] text-body font-medium text-accent underline-offset-4 transition-colors hover:text-accent-hover hover:underline md:mt-12"
            >
              {t('toContacts')} <ArrowRight aria-hidden size={20} />
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
