import Image from 'next/image';
import { FileText } from 'lucide-react';
import { getTranslations } from 'next-intl/server';
import type { SiteSettings } from '@/types/settings';
import { Container } from '@/components/ui/Container';
import { Logo } from '@/components/ui/Logo';
import { Link } from '@/i18n/navigation';
import { FOOTER_NAV } from './navigation';
import { TrackedLink } from './TrackedLink';

/** Подвал как на лендинге: меню, капсула с глобусом и контактами, юридические документы, реквизиты */
export async function Footer({ settings }: { settings: SiteSettings }) {
  const t = await getTranslations('footer');
  const th = await getTranslations('header');
  const year = new Date().getFullYear();
  const linkCls = 'transition-colors hover:text-accent';

  return (
    <footer className="mt-20 border-t border-border pb-8 pt-12 md:mt-30 lg:mt-40 lg:pt-16">
      <Container>
        <Link href="/" aria-label={th('home')} className="inline-block rounded-sm">
          <Logo alt="" className="h-12 md:h-16 lg:h-20" />
        </Link>

        <div className="mt-10 grid gap-10 lg:mt-14 lg:grid-cols-[1fr_auto_1fr] lg:items-center lg:gap-12">
          <nav aria-label={t('nav')}>
            <ul className="grid grid-cols-2 gap-x-6 gap-y-3 text-lg font-medium text-text sm:w-fit lg:grid-cols-1 lg:gap-y-2 lg:text-h4">
              {FOOTER_NAV.map((item) => (
                <li key={item.key}>
                  <Link href={item.href} className={linkCls}>
                    {t(`menu.${item.key}`)}
                  </Link>
                </li>
              ))}
            </ul>
          </nav>

          {/* Капсула с контактами */}
          <div className="flex w-fit max-w-full items-center gap-4 rounded-[60px] border border-accent p-2 pr-6 sm:gap-6 sm:rounded-pill sm:p-3 sm:pr-10">
            <div aria-hidden className="relative size-24 shrink-0 sm:size-32 lg:size-[156px]">
              <Image src="/images/footer/globe.svg" alt="" fill unoptimized className="object-contain" />
              <Image src="/images/footer/globe-text.svg" alt="" fill unoptimized className="animate-spin-slow object-contain" />
            </div>
            <ul className="flex min-w-0 flex-col gap-1.5 text-body font-medium text-text sm:text-lg">
              <li>
                <TrackedLink href={settings.phone.href} event="click_phone" params={{ place: 'footer' }} className={`${linkCls} whitespace-nowrap`}>
                  {settings.phone.display}
                </TrackedLink>
              </li>
              <li>
                <TrackedLink href={`mailto:${settings.emails.info}`} event="click_email" params={{ place: 'footer' }} className={`${linkCls} break-all`}>
                  {settings.emails.info}
                </TrackedLink>
              </li>
              <li>
                <TrackedLink href={`mailto:${settings.emails.order}`} event="click_email" params={{ place: 'footer' }} className={`${linkCls} break-all`}>
                  {settings.emails.order}
                </TrackedLink>
              </li>
            </ul>
          </div>

          <div className="flex flex-col gap-3 text-small text-text lg:items-end lg:text-right">
            <p className="text-caption uppercase tracking-[0.08em] text-text-secondary">{t('documents')}</p>
            <a href={settings.docs.consent} target="_blank" rel="noopener" className={`${linkCls} max-w-[260px]`}>
              {t('consent')}
              <span className="sr-only"> {t('newTab')}</span>
            </a>
            <a href={settings.docs.privacy} target="_blank" rel="noopener" className={linkCls}>
              {t('privacy')}
              <span className="sr-only"> {t('newTab')}</span>
            </a>
            <a href={settings.docs.card} target="_blank" rel="noopener" className={`${linkCls} inline-flex items-center gap-2`}>
              <FileText aria-hidden size={18} strokeWidth={1.5} className="text-accent" />
              {t('card')}
              <span className="sr-only"> {t('newTab')}</span>
            </a>
          </div>
        </div>

        <div className="mt-12 flex flex-col gap-1 text-small text-text-secondary md:flex-row md:gap-6">
          <p>{settings.address.full}</p>
          <p>{settings.hours}</p>
        </div>
        <p className="mt-6 border-t border-border pt-6 text-caption text-text-secondary">
          {t('copyright', {
            year,
            name: settings.legal.name,
            inn: settings.legal.inn,
            kpp: settings.legal.kpp,
            ogrn: settings.legal.ogrn,
          })}
        </p>
      </Container>
    </footer>
  );
}
