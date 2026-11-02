'use client';

import Image from 'next/image';
import * as RD from '@radix-ui/react-dialog';
import { ArrowRight, Mail, X } from 'lucide-react';
import { useTranslations } from 'next-intl';
import type { SiteSettings } from '@/types/settings';
import type { MenuSection } from '@/lib/site-menu';
import { Button } from '@/components/ui/Button';
import { ChevronDownIcon, PhoneOutgoingIcon } from '@/components/ui/DesignIcons';
import { Link } from '@/i18n/navigation';
import { track } from '@/lib/analytics';

/** Мобильное меню на весь экран: направления сайта аккордеоном, контакты, «Заказать». Язык — в подвале. */
export function MobileMenu({
  open,
  onOpenChange,
  menu,
  settings,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  menu: MenuSection[];
  settings: SiteSettings;
}) {
  const t = useTranslations('header');
  const tm = useTranslations('siteMenu');
  const close = () => onOpenChange(false);

  return (
    <RD.Root open={open} onOpenChange={onOpenChange}>
      <RD.Portal>
        <RD.Overlay className="fixed inset-0 z-[150] bg-base-deep/40 data-[state=open]:animate-fade-in lg:hidden" />
        <RD.Content
          aria-describedby={undefined}
          className="glass-overlay fixed inset-0 z-[151] flex flex-col overflow-y-auto overscroll-contain px-4 pb-10 pt-3 data-[state=open]:animate-sheet-up md:px-6 lg:hidden"
        >
          <div className="glass flex h-16 shrink-0 items-center justify-between rounded-pill pl-4 pr-2 sm:pr-3">
            <Link href="/" onClick={close} aria-label={t('home')}>
              <Image src="/images/brand/logo-eng.svg" alt="" width={132} height={46} unoptimized className="h-8 w-auto" />
            </Link>
            <RD.Title className="sr-only">{t('menuTitle')}</RD.Title>
            <RD.Close aria-label={t('closeMenu')} className="grid size-11 place-items-center rounded-full text-text hover:text-accent">
              <X aria-hidden size={24} strokeWidth={1.5} />
            </RD.Close>
          </div>

          <nav aria-label={t('mainNav')} className="mt-6">
            <ul>
              {menu.map((section) => (
                <li key={section.key} className="border-b border-border last:border-b-0">
                  <details className="group">
                    <summary className="flex cursor-pointer list-none items-center justify-between py-4 text-h4 font-medium text-text [&::-webkit-details-marker]:hidden">
                      {section.label}
                      <ChevronDownIcon size={22} className="text-accent transition-transform group-open:rotate-180" />
                    </summary>
                    <ul className="flex flex-col gap-1 pb-5">
                      {section.items.map((item) => (
                        <li key={item.href}>
                          <Link href={item.href} onClick={close} className="block py-2 text-body text-text-secondary hover:text-accent">
                            {item.label}
                          </Link>
                        </li>
                      ))}
                      <li className="mt-2">
                        <Link
                          href={(section.all ?? section).href}
                          onClick={close}
                          className="inline-flex items-center gap-2 py-2 text-body font-medium text-accent"
                        >
                          {section.all?.label ?? tm('openSection', { name: section.label })}
                          <ArrowRight aria-hidden size={18} strokeWidth={1.5} />
                        </Link>
                      </li>
                    </ul>
                  </details>
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
              <PhoneOutgoingIcon size={20} className="text-accent" />
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
            <Button href="/rfq/" size="m" onClick={close} className="mt-2 w-full">
              {t('order')}
            </Button>
          </div>
        </RD.Content>
      </RD.Portal>
    </RD.Root>
  );
}
