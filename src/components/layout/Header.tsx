'use client';

import { useEffect, useRef, useState } from 'react';
import Image from 'next/image';
import { Menu, X } from 'lucide-react';
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

/**
 * Шапка по макету Figma «Headder» (правки 02.11.2026): одна капсула с заливкой surface — логотип, «Меню», поиск,
 * телефон, корзина, «Заказать». «Меню» открывает направления сайта (SiteMenu); язык переключается в подвале.
 * <1024: логотип, поиск, корзина, бургер.
 */
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
        'fixed inset-x-0 top-3 z-[100] px-4 transition-[top] duration-300 md:px-6 lg:px-10',
        scrolled ? 'lg:top-3' : 'lg:top-10',
      )}
    >
      <div
        ref={wrapRef}
        className="relative mx-auto max-w-[1280px]"
        onBlur={(e) => {
          if (menuOpen && !e.currentTarget.contains(e.relatedTarget as Node | null)) setMenuOpen(false);
        }}
      >
        {/* Капсула */}
        <div className="relative isolate flex h-16 items-center justify-between gap-3 rounded-pill pl-4 pr-2 sm:pr-3 lg:h-[72px] lg:gap-8 lg:px-[22px]">
          {/* Стекло — отдельным слоем: размытие на самой капсуле не дало бы подсказкам поиска размыть страницу под собой */}
          <div aria-hidden className="glass absolute inset-0 -z-10 rounded-pill" />
          <div className="flex min-w-0 items-center gap-8 xl:gap-12">
            <Link href="/" aria-label={t('home')} className="shrink-0 rounded-sm">
              <Image src="/images/brand/logo-eng.svg" alt="" width={132} height={46} unoptimized priority className="h-8 w-auto lg:h-[37px]" />
            </Link>

            <div className="hidden min-w-0 items-center gap-4 lg:flex">
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
              <HeaderSearch variant="header" className="w-[430px] min-w-[180px] shrink" />
            </div>
          </div>

          <div className="flex shrink-0 items-center gap-1 sm:gap-2 lg:gap-6 xl:gap-12">
            <a
              href={settings.phone.href}
              onClick={() => track('click_phone', { place: 'header' })}
              aria-label={t('phoneLabel', { phone: settings.phone.display })}
              // На телефоне — иконка-кнопка 44 px рядом с поиском (аудит 11.11.2026): раньше звонок был только в меню
              className="inline-grid size-11 shrink-0 place-items-center text-body font-medium text-text transition-colors hover:text-accent lg:inline-flex lg:size-auto lg:gap-2.5"
            >
              <PhoneOutgoingIcon size={24} className="text-accent" />
              <span className="hidden whitespace-nowrap xl:inline">{settings.phone.display}</span>
            </a>

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

            <div className="flex items-center gap-1 sm:gap-2 lg:gap-4">
              <CartButton />
              <Link
                href="/rfq/"
                className="hidden h-10 shrink-0 items-center rounded-pill bg-accent pl-[31px] pr-[30px] text-body font-medium text-text-on-accent transition-colors hover:bg-accent-hover lg:inline-flex"
              >
                {t('order')}
              </Link>
            </div>

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
