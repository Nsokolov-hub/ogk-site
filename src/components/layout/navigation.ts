/** Пункты второй строки шапки и мобильного меню (ТЗ 11.2) */
export const MAIN_NAV = [
  { key: 'brands', href: '/brands/' },
  { key: 'services', href: '/services/' },
  { key: 'articles', href: '/articles/' },
  { key: 'about', href: '/about/' },
  { key: 'contacts', href: '/contacts/' },
] as const;

/** Меню подвала */
export const FOOTER_NAV = [
  { key: 'home', href: '/' },
  { key: 'catalog', href: '/catalog/' },
  { key: 'brands', href: '/brands/' },
  { key: 'services', href: '/services/' },
  { key: 'articles', href: '/articles/' },
  { key: 'about', href: '/about/' },
  { key: 'contacts', href: '/contacts/' },
  { key: 'order', href: '/rfq/' },
] as const;

/** Активен ли пункт меню для текущего адреса */
export function isActivePath(pathname: string, href: string) {
  if (href === '/') return pathname === '/';
  return pathname === href || pathname.startsWith(href) || `${pathname}/` === href;
}
