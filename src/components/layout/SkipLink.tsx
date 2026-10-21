import { useTranslations } from 'next-intl';

export function SkipLink() {
  const t = useTranslations('common');
  return (
    <a
      href="#main"
      className="fixed left-4 top-4 z-[300] -translate-y-24 rounded-pill bg-accent px-5 py-3 text-body font-semibold text-text-on-accent transition-transform focus-visible:translate-y-0"
    >
      {t('skipToContent')}
    </a>
  );
}
