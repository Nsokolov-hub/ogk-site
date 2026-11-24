import { getTranslations } from 'next-intl/server';
import { Button } from '@/components/ui/Button';
import { Container } from '@/components/ui/Container';
import { ArrowDownRightIcon } from '@/components/ui/DesignIcons';

export async function NotFoundBanner() {
  const t = await getTranslations('home.notFound');
  return (
    <section aria-labelledby="not-found-title" className="mt-16">
      <Container>
        <div className="not-found-banner flex flex-wrap items-center gap-8 rounded-block p-7 md:min-h-[264px] md:p-12 xl:gap-20 xl:px-20">
          <div>
            <h2 id="not-found-title" className="store-heading">
              {t.rich('title', { accent: (text) => <span className="text-accent">{text}</span> })}
            </h2>
            <p className="store-subtitle">
              {t.rich('text', { contact: (text) => <span className="text-text">{text}</span> })}
            </p>
          </div>
          <Button href="/contacts/" size="m" icon={<ArrowDownRightIcon size={24} />}>{t('cta')}</Button>
        </div>
      </Container>
    </section>
  );
}
