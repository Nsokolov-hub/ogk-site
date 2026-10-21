'use client';

import * as RD from '@radix-ui/react-dialog';
import { ArrowRight, ChevronDown, Mail, Phone, X } from 'lucide-react';
import { useTranslations } from 'next-intl';
import type { Category } from '@/types/catalog';
import type { SiteSettings } from '@/types/settings';
import { Button } from '@/components/ui/Button';
import { Logo } from '@/components/ui/Logo';
import { Link } from '@/i18n/navigation';
import { track } from '@/lib/analytics';
import { LangSwitcher } from './LangSwitcher';
import { MAIN_NAV } from './navigation';

/** Мобильное меню на весь экран: каталог аккордеоном, разделы, контакты, язык, «Заказать» */
export function MobileMenu({
  open,
  onOpenChange,
  tree,
  settings,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  tree: Category[];
  settings: SiteSettings;
}) {
  const t = useTranslations('header');
  const tm = useTranslations('megaMenu');
  const close = () => onOpenChange(false);

  return (
    <RD.Root open={open} onOpenChange={onOpenChange}>
      <RD.Portal>
        <RD.Overlay className="fixed inset-0 z-[150] bg-base-deep/70 data-[state=open]:animate-fade-in lg:hidden" />
        <RD.Content
          aria-describedby={undefined}
          className="fixed inset-0 z-[151] flex flex-col overflow-y-auto overscroll-contain bg-base px-4 pb-10 pt-3 data-[state=open]:animate-sheet-up md:px-6 lg:hidden"
        >
          <div className="flex h-16 shrink-0 items-center justify-between rounded-pill border border-border/60 bg-surface px-3 sm:px-4">
            <Link href="/" onClick={close} aria-label={t('home')}>
              <Logo alt="" className="h-8" />
            </Link>
            <RD.Title className="sr-only">{t('menuTitle')}</RD.Title>
            <RD.Close aria-label={t('closeMenu')} className="grid size-11 place-items-center rounded-full text-text hover:text-accent">
              <X aria-hidden size={24} strokeWidth={1.5} />
            </RD.Close>
          </div>

          <nav aria-label={t('mainNav')} className="mt-6">
            <details className="group">
              <summary className="flex cursor-pointer list-none items-center justify-between py-4 text-h4 font-medium text-text [&::-webkit-details-marker]:hidden">
                {t('catalog')}
                <ChevronDown aria-hidden size={22} strokeWidth={1.5} className="text-accent transition-transform group-open:rotate-180" />
              </summary>
              <ul className="flex flex-col gap-1 pb-5">
                {tree.map((c) => (
                  <li key={c.slug}>
                    <Link href={c.href} onClick={close} className="block py-2 text-body font-medium text-text hover:text-accent">
                      {c.name}
                    </Link>
                    {c.children?.length ? (
                      <ul className="mb-3 ml-1 flex flex-col pl-4">
                        {c.children.map((sub) => (
                          <li key={sub.slug}>
                            <Link href={sub.href} onClick={close} className="block py-1.5 text-small text-text-secondary hover:text-accent">
                              {sub.name}
                            </Link>
                          </li>
                        ))}
                      </ul>
                    ) : null}
                  </li>
                ))}
                <li className="mt-2">
                  <Link href="/catalog/" onClick={close} className="inline-flex items-center gap-2 py-2 text-body font-medium text-accent">
                    {tm('allCatalog')}
                    <ArrowRight aria-hidden size={18} strokeWidth={1.5} />
                  </Link>
                </li>
              </ul>
            </details>
            <ul>
              {MAIN_NAV.map((item) => (
                <li key={item.key}>
                  <Link href={item.href} onClick={close} className="block py-4 text-h4 font-medium text-text hover:text-accent">
                    {t(item.key)}
                  </Link>
                </li>
              ))}
            </ul>
          </nav>

          <div className="mt-8 flex flex-col gap-4">
            <a
              href={settings.phone.href}
              onClick={() => track('click_phone', { place: 'mobile_menu' })}
              className="inline-flex items-center gap-3 text-lg font-medium text-text"
            >
              <Phone aria-hidden size={20} strokeWidth={1.5} className="text-accent" />
              {settings.phone.display}
            </a>
            <a
              href={`mailto:${settings.emails.info}`}
              onClick={() => track('click_email', { place: 'mobile_menu' })}
              className="inline-flex items-center gap-3 text-lg text-text"
            >
              <Mail aria-hidden size={20} strokeWidth={1.5} className="text-accent" />
              {settings.emails.info}
            </a>
            <LangSwitcher className="w-fit" />
            <Button href="/rfq/" size="m" onClick={close} className="mt-2 w-full">
              {t('order')}
            </Button>
          </div>
        </RD.Content>
      </RD.Portal>
    </RD.Root>
  );
}
