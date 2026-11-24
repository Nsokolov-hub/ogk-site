'use client';

import { useEffect, useRef, useState } from 'react';
import Image from 'next/image';
import { Mail, Menu, X } from 'lucide-react';
import { useTranslations } from 'next-intl';
import type { SiteSettings } from '@/types/settings';
import type { MenuSection } from '@/lib/site-menu';
import { CartDrawer } from '@/components/rfq/CartDrawer';
import { ChevronDownIcon, ListIcon, PhoneOutgoingIcon, SearchIcon } from '@/components/ui/DesignIcons';
import { Link } from '@/i18n/navigation';
import { track } from '@/lib/analytics';
import { cn } from '@/lib/cn';
import { CartButton } from './CartButton';
import { HeaderSearch } from './HeaderSearch';
import { MobileMenu } from './MobileMenu';
import { SiteMenu } from './SiteMenu';

const iconBtn =
  'inline-grid size-11 shrink-0 place-items-center rounded-full text-text transition-colors hover:text-accent';

/** В узкой шапке телефон и почта для заказов занимают отдельную строку под навигацией. */
export function Header({ settings, menu }: { settings: SiteSettings; menu: MenuSection[] }) {
  const t = useTranslations('header');
  const [menuOpen, setMenuOpen] = useState(false);
  const [searchOpen, setSearchOpen] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);
  const [scrolled, setScrolled] = useState(false);
  const wrapRef = useRef<HTMLDivElement>(null);
  const menuBtnRef = useRef<HTMLButtonElement>(null);

  // В макете капсула стоит в 40 px от верха; при прокрутке она поднимается, чтобы не занимать экран
  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 24);
    onScroll();
    window.addEventListener('scroll', onScroll, { passive: true });
    return () => window.removeEventListener('scroll', onScroll);
  }, []);

  // Меню закрывается по Esc и по клику вне шапки
  useEffect(() => {
    if (!menuOpen) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        setMenuOpen(false);
        menuBtnRef.current?.focus();
      }
    };
    const onPointer = (e: PointerEvent) => {
      if (!wrapRef.current?.contains(e.target as Node)) setMenuOpen(false);
    };
    document.addEventListener('keydown', onKey);
    document.addEventListener('pointerdown', onPointer);
    return () => {
      document.removeEventListener('keydown', onKey);
      document.removeEventListener('pointerdown', onPointer);
    };
  }, [menuOpen]);

  return (
    <header
      className={cn(
        'fixed inset-x-0 top-3 z-[100] px-2 transition-[top] duration-300 sm:px-4 md:px-10',
        scrolled ? 'lg:top-3' : 'lg:top-10',
      )}
    >
      <div
        ref={wrapRef}
        className="relative mx-auto"
        onBlur={(e) => {
          if (menuOpen && !e.currentTarget.contains(e.relatedTarget as Node | null)) setMenuOpen(false);
        }}
      >
        {/* Капсула */}
        <div className="store-design-type relative isolate grid grid-cols-[minmax(0,1fr)_auto] items-center gap-x-2 rounded-[26px] px-3 pt-1 pb-1.5 min-[640px]:flex min-[640px]:h-[76px] min-[640px]:gap-4 min-[640px]:rounded-pill min-[640px]:py-0 md:px-10 lg:h-[90px] lg:gap-2 xl:gap-4 min-[1400px]:gap-6">
          {/* Стекло — отдельным слоем: размытие на самой капсуле не дало бы подсказкам поиска размыть страницу под собой */}
          <div aria-hidden className="glass absolute inset-0 -z-10 rounded-[inherit]" />
          <div className="flex min-w-0 items-center gap-4 min-[640px]:mr-auto lg:gap-3 xl:gap-4 min-[1400px]:gap-12">
            <Link href="/" aria-label={t('home')} className="shrink-0 rounded-sm">
              <Image src="/images/brand/logo-eng.svg" alt="" width={132} height={46} unoptimized priority className="h-8 w-auto lg:h-[46px] lg:w-[132px]" />
            </Link>

            <div className="hidden min-w-0 items-center gap-3 lg:flex xl:gap-4">
              <button
                ref={menuBtnRef}
                type="button"
                aria-expanded={menuOpen}
                aria-controls="site-menu"
                onClick={() => setMenuOpen((o) => !o)}
                className={cn(
                  'inline-flex h-10 shrink-0 items-center gap-2 rounded-pill border border-accent px-[14px] text-body font-medium transition-colors',
                  menuOpen ? 'bg-accent text-text-on-accent' : 'text-accent hover:bg-accent/10',
                )}
              >
                <ListIcon size={24} />
                {t('menu')}
                <ChevronDownIcon size={16} className={cn('transition-transform duration-300', menuOpen && 'rotate-180')} />
              </button>
              <HeaderSearch variant="header" className="w-[314px] min-w-[124px] shrink" />
            </div>
          </div>

          <div className="col-span-2 row-start-2 flex shrink-0 items-center justify-between gap-2 min-[640px]:gap-3 lg:gap-4 min-[1400px]:gap-6">
            <a
              href={settings.phone.href}
              onClick={() => track('click_phone', { place: 'header' })}
              aria-label={t('phoneLabel', { phone: settings.phone.display })}
              className="inline-flex min-h-7 shrink-0 items-center gap-1.5 whitespace-nowrap text-[13px] font-medium hover:text-accent min-[640px]:min-h-11 min-[640px]:min-w-11 min-[640px]:justify-center min-[640px]:text-body lg:gap-2.5"
            >
              <PhoneOutgoingIcon size={24} className="size-4 text-accent min-[640px]:size-6" />
              <span className="min-[640px]:hidden xl:inline">{settings.phone.display}</span>
            </a>

            <a
              href={`mailto:${settings.emails.order}`}
              aria-label={settings.emails.order}
              onClick={() => track('click_email', { place: 'header' })}
              className="inline-flex min-h-7 shrink-0 items-center gap-1.5 whitespace-nowrap text-sm font-medium text-accent min-[640px]:min-h-11 min-[640px]:gap-2 min-[640px]:text-text min-[640px]:hover:text-accent min-[640px]:text-body"
            >
              <Mail aria-hidden size={24} className="size-4 text-accent min-[640px]:size-6" />
              <span>{settings.emails.order}</span>
            </a>
          </div>

          <div className="col-start-2 row-start-1 flex shrink-0 items-center gap-1 sm:gap-2 lg:gap-4">
            <button
              type="button"
              className={cn(iconBtn, 'lg:hidden')}
              aria-label={searchOpen ? t('closeSearch') : t('openSearch')}
              aria-expanded={searchOpen}
              aria-controls="mobile-search"
              onClick={() => setSearchOpen((o) => !o)}
            >
              {searchOpen ? <X aria-hidden size={22} strokeWidth={1.5} /> : <SearchIcon size={22} />}
            </button>

            <CartButton />
            <Link
              href="/rfq/"
              className="hidden h-10 shrink-0 items-center rounded-pill bg-accent px-4 text-body font-medium text-text-on-accent transition-colors hover:bg-accent-hover lg:inline-flex xl:pl-[31px] xl:pr-[30px]"
            >
              {t('order')}
            </Link>

            <button
              type="button"
              className={cn(iconBtn, 'lg:hidden')}
              aria-label={t('openMenu')}
              aria-haspopup="dialog"
              onClick={() => setMobileOpen(true)}
            >
              <Menu aria-hidden size={24} strokeWidth={1.5} />
            </button>
          </div>
        </div>

        {menuOpen ? <SiteMenu id="site-menu" menu={menu} settings={settings} onNavigate={() => setMenuOpen(false)} /> : null}

        {searchOpen ? (
          <div id="mobile-search" className="glass-overlay mt-2 animate-fade-in rounded-pill p-1.5 lg:hidden">
            <HeaderSearch autoFocus />
          </div>
        ) : null}
      </div>

      <MobileMenu open={mobileOpen} onOpenChange={setMobileOpen} menu={menu} settings={settings} />
      <CartDrawer />
    </header>
  );
}
