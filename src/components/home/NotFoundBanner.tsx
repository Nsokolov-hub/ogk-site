import { FileUp } from 'lucide-react';
import { getTranslations } from 'next-intl/server';
import { Button } from '@/components/ui/Button';
import { Container } from '@/components/ui/Container';

export async function NotFoundBanner() {
  const t = await getTranslations('home.notFound');
  return (
    <section aria-labelledby="not-found-title" className="mt-16">
      <Container>
        <div className="flex flex-wrap items-center justify-between gap-8 rounded-block bg-[radial-gradient(circle_at_100%_50%,#203122,#111411_65%)] p-7 md:min-h-64 md:p-12 xl:px-20">
          <div>
            <h2 id="not-found-title" className="text-h2 font-medium">{t('title')}</h2>
            <p className="mt-4 text-lead text-text-secondary">{t('text')}</p>
          </div>
          <Button href="/rfq/#file" size="m" icon={<FileUp aria-hidden size={20} />}>{t('cta')}</Button>
        </div>
      </Container>
    </section>
  );
}
