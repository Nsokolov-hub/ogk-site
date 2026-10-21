'use client';

import { useEffect, useRef, useState } from 'react';
import { ChevronDown, LayoutGrid, Menu, Phone, Search, X } from 'lucide-react';
import { useTranslations } from 'next-intl';
import type { Category } from '@/types/catalog';
import type { SiteSettings } from '@/types/settings';
import { Button } from '@/components/ui/Button';
import { Container } from '@/components/ui/Container';
import { Logo } from '@/components/ui/Logo';
import { Link, usePathname } from '@/i18n/navigation';
import { track } from '@/lib/analytics';
import { cn } from '@/lib/cn';
import { CartButton } from './CartButton';
import { HeaderSearch } from './HeaderSearch';
import { LangSwitcher } from './LangSwitcher';
import { MegaMenu } from './MegaMenu';
import { MobileMenu } from './MobileMenu';
import { MAIN_NAV, isActivePath } from './navigation';

const iconBtn =
  'inline-grid size-11 shrink-0 place-items-center rounded-full text-text transition-colors hover:text-accent';

/**
 * Шапка (ТЗ 11.2). ≥1024: капсула (логотип, каталог, поиск, телефон, язык, корзина, «Заказать»)
 * и вторая строка меню, которая прячется при прокрутке вниз. <1024: логотип, поиск, корзина, бургер.
 */
export function Header({ settings, tree }: { settings: SiteSettings; tree: Category[] }) {
  const t = useTranslations('header');
  const pathname = usePathname();
  const [megaOpen, setMegaOpen] = useState(false);
  const [searchOpen, setSearchOpen] = useState(false);
  const [menuOpen, setMenuOpen] = useState(false);
  const [navHidden, setNavHidden] = useState(false);
  const wrapRef = useRef<HTMLDivElement>(null);
  const catalogBtnRef = useRef<HTMLButtonElement>(null);

  // Вторая строка меню уезжает при прокрутке вниз и возвращается при прокрутке вверх
  useEffect(() => {
    let lastY = window.scrollY;
    let ticking = false;
    const onScroll = () => {
      if (ticking) return;
      ticking = true;
      window.requestAnimationFrame(() => {
        const y = window.scrollY;
        if (Math.abs(y - lastY) > 8) {
          setNavHidden(y > 160 && y > lastY);
          lastY = y;
        }
        ticking = false;
      });
    };
    window.addEventListener('scroll', onScroll, { passive: true });
    return () => window.removeEventListener('scroll', onScroll);
  }, []);

  // Мегаменю закрывается по Esc и по клику вне шапки
  useEffect(() => {
    if (!megaOpen) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        setMegaOpen(false);
        catalogBtnRef.current?.focus();
      }
    };
    const onPointer = (e: PointerEvent) => {
      if (!wrapRef.current?.contains(e.target as Node)) setMegaOpen(false);
    };
    document.addEventListener('keydown', onKey);
    document.addEventListener('pointerdown', onPointer);
    return () => {
      document.removeEventListener('keydown', onKey);
      document.removeEventListener('pointerdown', onPointer);
    };
  }, [megaOpen]);

  const closeMega = () => setMegaOpen(false);

  return (
    <header className="fixed inset-x-0 top-3 z-[100]">
      <Container>
        <div
          ref={wrapRef}
          className="relative"
          onBlur={(e) => {
            if (megaOpen && !e.currentTarget.contains(e.relatedTarget as Node | null)) setMegaOpen(false);
          }}
        >
          {/* Капсула */}
          <div className="relative flex h-16 items-center gap-1.5 rounded-pill border border-border/60 bg-surface-raised/92 px-3 backdrop-blur-xl sm:gap-2 sm:px-4 lg:h-[72px] lg:gap-3 lg:px-5 xl:gap-4">
            <Link href="/" aria-label={t('home')} className="shrink-0 rounded-sm">
              <Logo alt="" className="h-8 lg:h-10" />
            </Link>

            <button
              ref={catalogBtnRef}
              type="button"
              aria-expanded={megaOpen}
              aria-controls="mega-menu"
              onClick={() => setMegaOpen((o) => !o)}
              className={cn(
                'ml-2 hidden h-10 shrink-0 items-center gap-2 rounded-pill border border-accent px-4 text-body font-medium transition-colors lg:inline-flex xl:ml-4',
                megaOpen ? 'bg-accent text-text-on-accent' : 'text-accent hover:bg-accent hover:text-text-on-accent',
              )}
            >
              <LayoutGrid aria-hidden size={18} strokeWidth={1.5} />
              {t('catalog')}
              <ChevronDown aria-hidden size={16} strokeWidth={1.5} className={cn('transition-transform', megaOpen && 'rotate-180')} />
            </button>

            {/* На главной поиск в шапке прячется, пока на экране большой поиск первого экрана (HeroSearch) */}
            <div className="hidden min-w-0 flex-1 lg:block">
              <div className="[html[data-hero-search=in]_&]:hidden">
                <HeaderSearch />
              </div>
            </div>
            <div className="flex-1 lg:hidden" />

            <a
              href={settings.phone.href}
              onClick={() => track('click_phone', { place: 'header' })}
              aria-label={t('phoneLabel', { phone: settings.phone.display })}
              className="hidden shrink-0 items-center gap-2 rounded-pill text-body font-medium text-text transition-colors hover:text-accent lg:inline-flex"
            >
              <Phone aria-hidden size={20} strokeWidth={1.5} className="text-accent" />
              <span className="hidden whitespace-nowrap 2xl:inline">{settings.phone.display}</span>
            </a>

            <LangSwitcher className="hidden lg:flex" />

            <button
              type="button"
              className={cn(iconBtn, 'lg:hidden')}
              aria-label={searchOpen ? t('closeSearch') : t('openSearch')}
              aria-expanded={searchOpen}
              aria-controls="mobile-search"
              onClick={() => setSearchOpen((o) => !o)}
            >
              {searchOpen ? <X aria-hidden size={22} strokeWidth={1.5} /> : <Search aria-hidden size={22} strokeWidth={1.5} />}
            </button>

            <CartButton />

            <Button href="/rfq/" size="s" className="hidden lg:inline-flex">
              {t('order')}
            </Button>

            <button
              type="button"
              className={cn(iconBtn, 'lg:hidden')}
              aria-label={t('openMenu')}
              aria-haspopup="dialog"
              onClick={() => setMenuOpen(true)}
            >
              <Menu aria-hidden size={24} strokeWidth={1.5} />
            </button>
          </div>

          {megaOpen ? <MegaMenu id="mega-menu" tree={tree} onNavigate={closeMega} /> : null}

          {searchOpen ? (
            <div id="mobile-search" className="mt-2 animate-fade-in rounded-pill bg-surface-raised p-1.5 lg:hidden">
              <HeaderSearch autoFocus />
            </div>
          ) : null}
        </div>

        {/* Вторая строка меню */}
        <nav
          aria-label={t('mainNav')}
          className={cn(
            'mt-2 hidden justify-center transition-[transform,opacity,visibility] duration-300 lg:flex',
            (navHidden || megaOpen) && 'invisible -translate-y-3 opacity-0',
          )}
        >
          <ul className="flex items-center gap-1 rounded-pill bg-surface-raised/95 p-1">
            {MAIN_NAV.map((item) => {
              const active = isActivePath(pathname, item.href);
              return (
                <li key={item.key}>
                  <Link
                    href={item.href}
                    aria-current={active ? 'page' : undefined}
                    className={cn(
                      'inline-flex h-9 items-center rounded-pill px-4 text-small font-medium transition-colors',
                      active ? 'bg-accent text-text-on-accent' : 'text-text hover:text-accent',
                    )}
                  >
                    {t(item.key)}
                  </Link>
                </li>
              );
            })}
          </ul>
        </nav>
      </Container>

      <MobileMenu open={menuOpen} onOpenChange={setMenuOpen} tree={tree} settings={settings} />
    </header>
  );
}
