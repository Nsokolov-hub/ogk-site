import { useTranslations } from 'next-intl';
import { Button } from '@/components/ui/Button';
import { Container } from '@/components/ui/Container';

/** Временная 404. Полную версию с поиском и популярными категориями (SEO-05) сделаем отдельно. */
export default function NotFound() {
  const t = useTranslations('notFound');
  return (
    <Container className="flex min-h-[70svh] flex-col items-start justify-center pb-16 pt-40">
      {/* React 19 поднимает title и meta в head */}
      <title>{`${t('title')} — ОГК-ХИМ`}</title>
      <meta name="robots" content="noindex" />
      <p className="text-h1 font-medium text-accent">404</p>
      <h1 className="mt-4 text-h2 font-medium text-text">{t('title')}</h1>
      <p className="mt-4 max-w-[560px] text-lead text-text-secondary">{t('text')}</p>
      <div className="mt-8 flex flex-wrap gap-3">
        <Button href="/" size="m">
          {t('home')}
        </Button>
        <Button href="/catalog/" variant="menu" size="m">
          {t('catalog')}
        </Button>
      </div>
    </Container>
  );
}
